import json
from datetime import datetime, timedelta

import falcon
import requests
from kubernetes import client, config

config.load_incluster_config()
KUBE_API = client.CoreV1Api()

LOAD_CHECKING_INTERVAL = 3 * 60  # Amount of seconds to go back when averaging load for choosing least busy container


class Test:
    def on_get(self, req, resp):
        return


class Worker:
    def on_get(self, req, resp):
        pods = req.media
        if not pods:
            resp.status = falcon.HTTP_400
            resp.body = 'Body should contain pod objects'
            return

        # Get worker performance
        res = requests.get('http://mongoapi:8000/query/performance', data=json.dumps({
            'usage.time': {'$gte': (datetime.utcnow() - timedelta(seconds=LOAD_CHECKING_INTERVAL)).isoformat()},
            'container': {'$in': list(map(lambda pod: pod['container'], pods))},
            '$sort': [('usage.time', -1)]
        }))

        # If failed, return first pod
        if res.status_code != 200 or not res.json():
            resp.body = json.dumps(pods[0])
            return

        # Aggregate performances for each container
        performance = {}
        for entry in res.json():
            container = entry['container']
            if container not in performance:
                performance[container] = {'cpu': 0, 'memory': 0, 'count': 0}
            performance[container]['cpu'] += entry['usage']['cpu']
            performance[container]['memory'] += entry['usage']['memory']
            performance[container]['count'] += 1

        # Average CPU and memory load
        for perf in performance.values():
            perf['cpu'] /= perf['count']
            perf['memory'] /= perf['count']
            del perf['count']

        # The selection could be better if the QoS knew whether the job is CPU or memory intensive.
        # Currently, selection takes place by averaging CPU and memory load and taking the lowest.
        # Thus, it is assumed that CPU and memory have the same weight in the selection.
        selected_container = min(performance.items(), key=lambda tup: tup[1]['cpu'] + tup[1]['memory'] / 2)[0]
        resp.body = json.dumps(list(filter(lambda pod: pod['container'] == selected_container, pods))[0])


api = falcon.API()
workerResource = Worker()
api.add_route('/test', Test())
api.add_route('/worker', workerResource)
