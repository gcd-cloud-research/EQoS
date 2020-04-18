""""This service runs outside of the cluster on net=host or a mapped port."""
import json

from flask import Flask, request, abort
import requests
from kubernetes import client, config

config.load_kube_config(config_file='/kube/config')
KUBE_API = client.CoreV1Api()
QOS = None
app = Flask(__name__)

ROUTE_MAP = {
    'mongo': 'mongoapi',
    'routine': 'producer'
}

ALLOWED_ROUTES = [
    r'^mongo/query',
    r'^routine$'
]


class LitePod:
    class Encoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

    def __init__(self, name, ip, labels):
        self.name = name
        self.host_ip = ip
        self.labels = labels

    def __str__(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def pod_to_lite_pod(pod):
        return LitePod(pod.metadata.name, pod.status.host_ip, pod.metadata.labels)

    @staticmethod
    def decode(o):
        return LitePod(o['name'], o['host_ip'], o['labels'])


def is_allowed(route):
    from re import match
    return len(
        list(
            filter(lambda r: match(r, route), ALLOWED_ROUTES)
        )
    ) > 0


def get_port(pod):
    label = 'io.kompose.service=%s' % pod.labels['io.kompose.service']
    ports = list(filter(
        lambda candidate_port: candidate_port.name == 'serviceport',
        KUBE_API.list_namespaced_service('default', label_selector=label).items[0].spec.ports
    ))
    if len(ports) == 0:
        raise RuntimeError("No service available for pod with label %s" % label)
    return ports[0].node_port


def get_qos():
    qos_pods = get_available_pods('qos')
    if len(qos_pods) == 0:
        raise RuntimeError("QoS pod not found")
    qos_pod = qos_pods[0]
    return '%s:%s' % (qos_pod.host_ip, get_port(qos_pod))


def get_available_pods(service):
    label = 'io.kompose.service=%s' % service
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
    return list(map(
        lambda pod: LitePod.pod_to_lite_pod(pod),
        pods
    ))


def get_best_host(service_name):
    """Request best worker (host:port) to QoS service."""
    global QOS
    pods = get_available_pods(service_name)

    # Get best host
    res = None
    while not res:
        # If requests does not work, find QOS. If it does not exist, get_qos raises RuntimeError. So
        # it loops twice at most.
        try:
            res = requests.get('http://%s/worker' % QOS, data=json.dumps(pods, cls=LitePod.Encoder))
        except requests.exceptions.ConnectionError:
            QOS = get_qos()

    if res.status_code != 200:
        return res.status_code, None
    best_pod = LitePod.decode(res.json())
    return res.status_code, '%s:%s' % (best_pod.host_ip, get_port(best_pod))


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def on_request(path):
    if not path:  # If /, return 200 (for testing)
        return ''

    if not is_allowed(path):
        abort(401)
        return

    service, route = path.split('/', maxsplit=1)

    # Get the service related to this path
    mapped_service = ROUTE_MAP[service] if service in ROUTE_MAP else ''
    if not mapped_service:
        abort(404)
        return

    # Get appropriate worker for service
    app.logger.info("Getting best host for %s" % mapped_service)
    status, host = get_best_host(mapped_service)
    if status != 200:
        abort(status)
        return
    app.logger.info("Got best host: %s" % host)

    # Add files if necessary
    files = {}
    if 'program' in request.files:
        files['program'] = request.files['program']

    # Route request
    req = requests.request(request.method, 'http://%s/%s' % (host, route), data=request.get_json(), files=files)
    app.logger.info("Response received: %d" % req.status_code)

    # Process response
    return req.text


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
