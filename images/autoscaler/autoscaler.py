import os
from datetime import datetime, timedelta
from signal import alarm, pause, SIGALRM, signal
from time import sleep
import requests
import requests.exceptions as ex
import logging
import json
import sys
from kubernetes import client
from kubernetes.config import load_incluster_config
from plugins import PluginManager

load_incluster_config()
KUBE_CLIENT = client.AppsV1Api()

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
received = False


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
            exclude=("monitor",),
            over_threshold=0.5,
            under_threshold=0.5
    ):
        self.update_seconds = u_s
        self.scaling = scaling
        self.exclude = exclude
        self.over_threshold = over_threshold
        self.under_threshold = under_threshold

    @staticmethod
    def load(json_file):
        with open(json_file) as fh:
            json_obj = json.load(fh)
        json_obj['scaling'] = from_json(Config.ScalingConfig, json_obj['scaling'])
        return from_json(Config, json_obj)

    def __str__(self):  # Used for debugging
        return json.dumps(self, cls=Config.Encoder)


class JsonStreamIterator:
    # Does not accept lists as items, as it only needs to process performance objects
    def __init__(self, response):
        self.ite = response.iter_content(decode_unicode=True)

    def __iter__(self):
        return self

    def __next__(self):
        string = ''
        open_count = 0
        for char in self.ite:
            string += char.decode('utf-8')
            if string[-1] == '{':
                open_count += 1
            if string[-1] == '}':
                open_count -= 1
                if not open_count:
                    break
        if not string:
            raise StopIteration()
        return json.loads(string)


def monitor_containers(config, wpipe):
    global received
    stepback_time = timedelta(seconds=config.update_seconds)
    plugin_manager = PluginManager(config)
    while True:
        alarm(config.update_seconds)
        received = False
        res = None
        try:
            res = requests.get(
                'http://mongoapi:8000/query/performance',
                data=json.dumps({
                    'usage.time': {'$gte': (datetime.utcnow() - stepback_time).isoformat()},
                    'container': {'$exists': True},
                    '$sort': [('usage.time', 1)]
                }),
                timeout=config.update_seconds / 2,
                stream=True
            )
            logging.debug("Received response. Time: %d" % res.elapsed.total_seconds())
        except (ex.ConnectionError, ex.ConnectTimeout, ex.ReadTimeout) as e:
            logging.warning("Could not connect to mongoapi: %s" % e)
            os.write(wpipe, ';\n'.encode('utf-8'))

        if not res:
            pass
        elif res.status_code != 200:
            logging.warning("Received code %d from internaldb: %s" % (res.status_code, res.text))
            stepback_time += timedelta(seconds=config.update_seconds)  # In next request, ask for all missing data
            res.close()

        else:
            # Pod is overloaded if one container is overloaded.
            # Pod is underloaded if all containers are underloaded
            pods = {}
            for measurement in JsonStreamIterator(res):
                if measurement['pod'] not in pods:
                    pods[measurement['pod']] = 0

                # If we know that pod is overloaded, we can skip all other containers
                if pods[measurement['pod']] > 0:
                    continue

                # Find out if container is overloaded (1), underloaded (-1), or fine (0)
                load = plugin_manager.calculate_load(measurement['container'], measurement['usage'])

                # If pod is underloaded, its value will be the number of containers, negative
                pods[measurement['pod']] = 1 if load == 1 else pods[measurement['pod']] + load

            res.close()

            # Aggregate all pods under their respective deployment
            deps = filter(
                lambda name: name in ' '.join(pods.keys()),  # Only get deployments that have been measured
                get_deployment_names()
            )
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
        if not received:
            pause()


def get_desired_replicas(deployment):
    dep_data = KUBE_CLIENT.read_namespaced_deployment(deployment, 'default')
    return int(dep_data.metadata.labels['io.kubernetes.replicas']) \
        if 'io.kubernetes.replicas' in dep_data.metadata.labels \
        else 1


def scale_from_pipe(rpipe, whitelist):
    from copy import deepcopy
    fh = os.fdopen(rpipe)
    base_values = init_desired_replicas(whitelist)
    desired = deepcopy(base_values)
    while True:
        readval = fh.readline().strip()
        logging.debug(readval)
        if readval:
            logging.debug("Received %s" % readval)
            replicas = {}
            for dep, adjustment in \
                    [(entry.split(',')[0], int(entry.split(',')[1])) for entry in readval.split(';')] if readval != ';'\
                    else []:
                if dep in whitelist:
                    continue
                # Update desired replicas if base values have changed
                new_val = get_desired_replicas(dep)
                if new_val != base_values[dep]:
                    # Change desired replicas based on perceived increment or decrement
                    desired[dep] += new_val - base_values[dep]
                    base_values[dep] = new_val

                # Get current number of desired replicas by Kubernetes
                kube_des_rep = KUBE_CLIENT.read_namespaced_deployment_scale(dep, 'default').spec.replicas

                # Get desired number of replicas by us
                our_des_rep = desired[dep] + adjustment
                our_des_rep = our_des_rep if our_des_rep > 0 else 1
                logging.debug("Deployment %s:\n\tIn kubernetes: %d\n\tDesired: %d" % (dep, kube_des_rep, our_des_rep))

                # Record deployments in which desires differ
                if kube_des_rep != our_des_rep:
                    replicas[dep] = our_des_rep

            # Where Kubernetes desires differently, make it change its wishes
            # Or if that is what was asked, redo all
            replicas = replicas if readval != ';' else desired
            for dep, objective in replicas.items():
                logging.info("Scaling %s to %d" % (dep, objective))
                KUBE_CLIENT.patch_namespaced_deployment_scale(dep, 'default', json.loads(
                    '{"spec": { "replicas": %d }}' % objective
                ))
                desired[dep] = objective
        else:
            sleep(1)


def get_deployment_names():
    deployments = KUBE_CLIENT.list_namespaced_deployment('default').items
    return list(map(lambda d: d.metadata.name, deployments))


def init_desired_replicas(whitelist):
    desired = {}
    for dep in filter(lambda name: name not in whitelist, get_deployment_names()):
        desired[dep] = get_desired_replicas(dep)
    return desired


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'config.json'

    conf = Config.load(filename)

    def sign_received(sig, frame):
        global received
        received = True
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
            signal(SIGALRM, sign_received)
            monitor_containers(conf, wscale)
        else:
            pid, status = os.wait()
            logging.error("Child %d crashed with status %d (%x). Restarting" % (pid, status, status))
