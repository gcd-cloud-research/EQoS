import json

import falcon
from kubernetes import client, config

config.load_kube_config()
KUBE_API = client.CoreV1Api()


class Test:
    def on_get(self, req, resp):
        return


class Worker:
    @staticmethod
    def get_best(pod_list):
        return pod_list[0]

    def on_get(self, req, resp):
        qs = req.params
        if 'service' not in qs:
            resp.status = falcon.HTTP_400
            resp.body = 'Parameter "service" not found'
            return

        label = 'io.kompose.service=%s' % qs['service']
        # Get available pods
        pods = filter(  # Include only pods that have a running container
            lambda pod: len(list(filter(  # Check if any container in pod has status 'running'
                lambda running: running is not None,
                map(  # Get list of 'running' statuses from containers in pod
                    lambda cont_status: cont_status.state.running,
                    pod.status.container_statuses
                )
            ))),
            KUBE_API.list_namespaced_pod('default', label_selector=label).items
        )
        pods = list(pods)

        # If no pods available, 404
        if len(pods) == 0:
            resp.status = falcon.HTTP_404
            return

        # Select best pod
        pod = Worker.get_best(pods)

        # Get port of selected pod
        ports = list(filter(
            lambda candidate_port: candidate_port.name == 'serviceport',
            KUBE_API.list_namespaced_service('default', label_selector=label).items[0].spec.ports
        ))
        print(KUBE_API.list_namespaced_service('default', label_selector=label).items[0].spec.ports)
        if len(ports) == 0:
            resp.status = falcon.HTTP_404
            return
        port = ports[0].node_port

        # Set response body
        resp.body = json.dumps({
            'host': pod.status.host_ip,
            'port': port
        })
        print(resp.body)


api = falcon.API()
workerResource = Worker()
api.add_route('/test', Test())
api.add_route('/worker', workerResource)
