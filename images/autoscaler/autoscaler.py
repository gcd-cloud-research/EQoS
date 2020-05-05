import os
from datetime import datetime, timedelta
from signal import alarm, pause, SIGALRM, signal
from time import sleep
import requests
import logging
import json
import sys
from kubernetes import client
from kubernetes.config import load_incluster_config

load_incluster_config()
KUBE_CLIENT = client.AppsV1Api()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


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
            scaling=ScalingConfig(),
            exclude=("monitor",)
    ):
        self.update_seconds = u_s
        self.scaling = scaling
        self.exclude = exclude

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
        over, self.overloaded = self._load_check(
            self.overloaded,
            lambda u: u > self.config.max_load,
            container, usage
        )
        under, self.underloaded = self._load_check(
            self.underloaded,
            lambda u: u < self.config.min_load,
            container, usage
        )

        if over:
            return 1  # Container overloaded
        if under:
            return -1  # Container underloaded
        return 0  # Normal

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
            # Pod is overloaded if one container is overloaded.
            # Pod is underloaded if all containers are underloaded
            pods = {}
            for measurement in res.json():
                if measurement['pod'] not in pods:
                    pods[measurement['pod']] = 0

                # If we know that pod is overloaded, we can skip all other containers
                if pods[measurement['pod']] > 0:
                    continue

                # Find out if container is overloaded (1), underloaded (-1), or fine (0)
                load = load_tracker.process_usage(measurement['container'], measurement['usage'])

                # If pod is underloaded, its value will be the number of containers, negative
                pods[measurement['pod']] = 1 if load == 1 else pods[measurement['pod']] + load

            # Aggregate all pods under their respective deployment
            deps = set(map(lambda pod: pod.split('-')[0], pods.keys()))
            from functools import reduce
            buffer = ";".join([
                '%s,%d' % (
                    dep,
                    reduce(
                        lambda acc, val: acc + val,
                        map(
                            lambda poditem: poditem[1],
                            filter(
                                lambda poditem: dep in poditem[0],
                                pods.items()
                            )
                        )
                    )
                )
                for dep in deps
            ])
            logging.debug(buffer)
            os.write(wpipe, (buffer + '\n').encode('utf-8'))
        pause()


def get_desired_replicas(deployment):
    dep_data = KUBE_CLIENT.read_namespaced_deployment(deployment, 'default')
    return dep_data.metadata.labels['io.kuberentes.replicas'] \
        if 'io.kubernetes.replicas' in dep_data.metadata.labels \
        else 1


def scale_from_pipe(rpipe, whitelist):
    fh = os.fdopen(rpipe)
    desired = {}
    while True:
        readval = fh.readline().strip()
        if readval:
            logging.debug("Received %s" % readval)
            replicas = {}
            for dep, adjustment in [(entry.split(',')[0], int(entry.split(',')[1])) for entry in readval.split(';')]:
                if dep in whitelist:
                    continue
                # Get current number of desired replicas by Kubernetes
                kube_des_rep = KUBE_CLIENT.read_namespaced_deployment_scale(dep, 'default').spec.replicas

                # Get desired number of replicas by us
                if dep not in desired:
                    desired[dep] = get_desired_replicas(dep)
                our_des_rep = desired[dep] + adjustment
                our_des_rep = our_des_rep if our_des_rep > 0 else 1
                logging.info("Deployment %s:\n\tIn kubernetes: %d\n\tDesired: %d" % (dep, kube_des_rep, our_des_rep))

                # Record deployments in which desires differ
                if kube_des_rep != our_des_rep:
                    replicas[dep] = our_des_rep

            # Where Kubernetes desires differently, make it change its wishes
            for dep, objective in replicas.items():
                logging.info("Scaling %s to %d" % (dep, objective))
                KUBE_CLIENT.patch_namespaced_deployment_scale(dep, 'default', json.loads(
                    '{"spec": { "replicas": %d }}' % objective
                ))
                desired[dep] = objective
        else:
            sleep(1)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'config.json'

    conf = Config.load(filename)

    def sign_debug(sig, frame):
        print(logging.debug("(ALRM: %d) Received signal %d" % (SIGALRM, sig)))

    rscale, wscale = os.pipe()
    if os.fork() == 0:
        os.close(wscale)
        while True:
            if os.fork() == 0:
                scale_from_pipe(rscale, conf.exclude)
            else:
                logging.error("Child %d crashed with status %d" % (os.wait()))
    os.close(rscale)

    while True:
        if os.fork() == 0:
            signal(SIGALRM, sign_debug)
            monitor_containers(conf, wscale)
        else:
            pid, status = os.wait()
            logging.error("Child %d crashed with status %d (%x). Restarting" % (pid, status, status))
