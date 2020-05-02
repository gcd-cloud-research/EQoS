from datetime import datetime, timedelta
from signal import alarm, pause
import requests
import logging

from kubernetes import client, config as kubeconfig
import json
import sys

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


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
                tolerance=5
        ):
            self.min_load = min_load
            self.max_load = max_load
            self.max_load_nowait = max_load_nowait
            self.wait_seconds = wait_seconds
            self.tolerance = tolerance

    def __init__(
            self,
            u_s=5,
            scaling=ScalingConfig()
    ):
        self.update_seconds = u_s
        self.scaling = scaling

    @staticmethod
    def load(filename):
        with open(filename) as fh:
            json_obj = json.load(fh)
        json_obj['scaling'] = from_json(Config.ScalingConfig, json_obj['scaling'])
        return from_json(Config, json_obj)

    def __str__(self):  # Used for debugging
        return json.dumps(self, cls=Config.Encoder)


class LoadTracker:
    def __init__(self, config):
        self.overloaded = {}  # Key: container name. Value: number of times the container has not been overloaded
        self.underloaded = {}  # Key: container name. Value: number of times the container has not been underloaded
        self.config = config.scaling
        self.threshold = config.scaling.wait_seconds / config.update_seconds

    def process_performances(self, performances):
        scale = []
        descale = []
        # Update overloaded and underloaded objects
        for container, usage_list in performances.items():
            for usage in usage_list:
                scale += [container] if self._overload(container, usage) else []
                descale += [container] if self._underload(container, usage) else []

        return scale, descale

    def _overload(self, container, usage):
        # If container is over threshold, add to overloaded
        if max(usage['cpu'], usage['memory']) > self.config.max_load:
            self.overloaded, ret_val = self._increment_count(
                container,
                self.overloaded,
                1 if max(usage['cpu'], usage['memory']) < self.config.max_load_nowait else self.threshold
            )
            return ret_val

        # Otherwise, if it is in overloaded, increment count and remove if tolerance is reached
        elif container in self.overloaded.keys():
            self.overloaded[container][1] += 1
            if self.overloaded[container][1] >= self.config.tolerance:
                del self.overloaded[container]

        return False

    def _underload(self, container, usage):
        # If container is under threshold, add to underloaded
        if max(usage['cpu'], usage['memory']) < self.config.min_load:
            self.underloaded, ret_val = self._increment_count(container, self.underloaded)
            return ret_val

        # Otherwise, if it is in underloaded, increment count and remove if tolerance is reached
        elif container in self.underloaded.keys():
            self.underloaded[container][1] += 1
            if self.underloaded[container][1] >= self.config.tolerance:
                del self.underloaded[container]

        return False

    def _increment_count(self, container, target_dict, inc_val=1):
        if container not in target_dict.keys():
            target_dict[container] = [0, 0]  # [<exceptional load count>, <normal load count>]
        target_dict[container][0] += inc_val
        if target_dict[container][0] >= self.threshold:
            del target_dict[container]
            return target_dict, True
        return target_dict, False


def to_container_dict(json_data):
    result = {}
    for entry in json_data:
        if entry['container'] not in result:
            result[entry['container']] = []
        result[entry['container']].append(entry['usage'])
    return result


def monitor_containers(config):
    stepback_time = timedelta(seconds=config.update_seconds)
    load_tracker = LoadTracker(config)
    while True:
        alarm(config.update_seconds)

        res = requests.get(
            'http://mongoapi:8000/query/performance',
            data=json.dumps({
                'usage.time': {'$gte': datetime.utcnow() - stepback_time},
                '$sort': [('container', 1)]
            }),
            timeout=config.update_seconds / 2
        )

        if res.status_code != 200:
            logging.warning("Received code %d from mongoapi: %s" % (res.status_code, res.text))
            stepback_time += timedelta(seconds=config.update_seconds)  # In next request, ask for all missing data

        else:
            scale, descale = load_tracker.process_performances(to_container_dict(res.json()))
        pause()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'config.json'

    print(Config.load(filename))

    with open("testperformance.json") as fh:
        x = json.load(fh)
    l = LoadTracker(Config.load(filename))
    print(l.process_performances(to_container_dict(x)))
