import json

import falcon
from kubernetes import client, config

config.load_incluster_config()
KUBE_API = client.CoreV1Api()


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

        # Get best worker
        resp.body = json.dumps(pods[0])


api = falcon.API()
workerResource = Worker()
api.add_route('/test', Test())
api.add_route('/worker', workerResource)
