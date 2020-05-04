import os
from datetime import datetime, timedelta
from signal import alarm, pause, SIGALRM, signal
from time import sleep
import requests
import logging
import json
import sys

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def fromisoformat(usage_time):
    return datetime.fromisoformat(usage_time[:usage_time.find('.') + 4])


def from_json(class_to_instantiate, json_obj):
    c = class_to_instantiate()
    for key, value in json_obj.items():
        if key in c.__dict__.keys():
            c.__dict__[key] = value
    return c


class Config:
    class Encoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

    class ScalingConfig:
        def __init__(
                self,
                min_load=0.4,
                max_load=0.8,
                max_load_nowait=0.9,
                wait_seconds=60,
                tolerance=5,
                grace=30
        ):
            self.min_load = min_load
            self.max_load = max_load
            self.max_load_nowait = max_load_nowait
            self.wait_seconds = wait_seconds
            self.tolerance = tolerance
            self.grace_period = grace

    def __init__(
            self,
            u_s=5,
            scaling=ScalingConfig()
    ):
        self.update_seconds = u_s
        self.scaling = scaling

    @staticmethod
    def load(json_file):
        with open(json_file) as fh:
            json_obj = json.load(fh)
        json_obj['scaling'] = from_json(Config.ScalingConfig, json_obj['scaling'])
        return from_json(Config, json_obj)

    def __str__(self):  # Used for debugging
        return json.dumps(self, cls=Config.Encoder)


class LoadTracker:
    def __init__(self, config):
        self.overloaded = {}
        self.underloaded = {}
        self.grace = {}
        self.config = config.scaling
        self.threshold = config.scaling.wait_seconds / config.update_seconds

    def process_usage(self, container, usage):
        if container in self.grace:
            # If grace period is exceeded by measurements, remove container from grace
            if self.grace[container] < fromisoformat(usage['time']):
                del self.grace[container]
            # Otherwise, do not process usage
            else:
                return 0

        # If container is over immediate scale threshold, scale and add to grace
        if max(usage['cpu'], usage['memory']) > self.config.max_load_nowait:
            if container in self.overloaded:
                del self.overloaded[container]
                self.grace[container] = fromisoformat(usage['time']) + \
                    timedelta(seconds=self.config.grace_period)
            return 1

        # Check if scaling or descaling is needed (only one can be True)
        scale, self.overloaded = self._load_check(
            self.overloaded,
            lambda u: u > self.config.max_load,
            container, usage
        )
        descale, self.underloaded = self._load_check(
            self.underloaded,
            lambda u: u < self.config.min_load,
            container, usage
        )

        if scale:
            return 1  # Scale up
        if descale:
            return -1  # Scale down
        return 0  # Do nothing

    def _load_check(self, load_object, criteria, container, usage):
        # If usage means exceptional load...
        if criteria(max(usage['cpu'], usage['memory'])):
            # If not in object, add
            if container not in load_object:
                load_object[container] = LoadTracker._new_load_object(usage['time'])

            # If it is in object and time > wait_seconds, scale and add to grace
            elif fromisoformat(usage['time']) > \
                    load_object[container]['start_time'] + timedelta(seconds=self.config.wait_seconds):
                del load_object[container]
                self.grace[container] = fromisoformat(usage['time']) + \
                    timedelta(seconds=self.config.grace_period)
                return True, load_object

        # If usage means no exceptional load, but container is in object, increment normal load counter
        elif container in load_object:
            load_object[container]['normal_load_count'] += 1
            # If tolerance is reached, remove from overloaded
            if load_object[container]['normal_load_count'] >= self.config.tolerance:
                del load_object[container]

        return False, load_object  # Catch-all for non-scaling cases

    @staticmethod
    def _new_load_object(time):
        return {
            'start_time': fromisoformat(time),
            'normal_load_count': 0
        }


def monitor_containers(config, wpipe):
    stepback_time = timedelta(seconds=config.update_seconds)
    load_tracker = LoadTracker(config)
    while True:
        alarm(config.update_seconds)

        res = requests.get(
            'http://mongoapi:8000/query/performance',
            data=json.dumps({
                'usage.time': {'$gte': (datetime.utcnow() - stepback_time).isoformat()},
                'container': {'$exists': True},
                '$sort': [('usage.time', 1)]
            }),
            timeout=config.update_seconds / 2
        )

        logging.debug("Received %d documents" % (len(res.json())))

        if res.status_code != 200:
            logging.warning("Received code %d from internaldb: %s" % (res.status_code, res.text))
            stepback_time += timedelta(seconds=config.update_seconds)  # In next request, ask for all missing data

        else:
            for measurement in res.json():
                scale_val = load_tracker.process_usage(measurement['container'], measurement['usage'])
                if scale_val != 0:
                    logging.info("Container %s in pod %s should be %sscaled" % (
                        measurement['container'],
                        measurement['pod'],
                        'de' if scale_val < 0 else ''
                    ))
                    os.write(wpipe, ('%s:%d\n' % (measurement['container'], scale_val)).encode('utf-8'))
                logging.debug("No actions needed for %s in %s" % (measurement['container'], measurement['pod']))
        pause()


def scale_from_pipe(rpipe):
    from kubernetes import client, config
    config.load_incluster_config()
    c = client.ExtensionsV1beta1Api()
    fh = os.fdopen(rpipe)
    while True:
        readval = fh.readline().strip()
        if readval:
            container, scale_val = readval.split(':')
            logging.debug("Scaling %s by %d" % (container, scale_val))
            # c.read_namespaced_deployment_scale(, 'default')
            # c.replace_namespaced_deployment(, 'default', )
        else:
            sleep(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'config.json'

    def sign_debug(sig, frame):
        print(logging.debug("(ALRM: %d) Received signal %d" % (SIGALRM, sig)))

    rscale, wscale = os.pipe()
    if os.fork() == 0:
        os.close(wscale)
        scale_from_pipe(rscale)
    os.close(rscale)

    while True:
        if os.fork() == 0:
            signal(SIGALRM, sign_debug)
            monitor_containers(Config.load(filename), wscale)
        else:
            pid, status = os.wait()
            logging.error("Child %d crashed with status %d (%x). Restarting" % (pid, status, status))
