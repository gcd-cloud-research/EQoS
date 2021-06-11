""""This service runs outside of the cluster on net=host or a mapped port."""
import json
import os

from flask import Flask, request, abort, jsonify
import requests
from kubernetes import client, config
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch, helpers

config.load_kube_config(config_file='/kube/config')
KUBE_API = client.CoreV1Api()
QOS = None
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "/tmp"
ALLOWED_EXTENSIONS = ['txt', 'py', 'r']
POSSIBLE_FILES = ['program', 'requirements']

es = Elasticsearch([
    'monitornode.eqos:9200'
])

ROUTE_MAP = {
    'mongo': 'mongoapi',
    'routine': 'producer'
}

ALLOWED_ROUTES = [
    r'^mongo/query/tasks',
    r'^mongo/query/performance',
    r'^mongo/taskperformance',
    r'^mongo/taskstatus',
    r'^routine$'
]


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


class LitePod:
    """Assumes pods have at least one running container, as checked in get_available_pods"""
    class Encoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

    def __init__(self, name, ip, labels, container):
        self.name = name
        self.host_ip = ip
        self.labels = labels
        self.container = container

    def __str__(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def pod_to_lite_pod(pod):
        return LitePod(
            pod.metadata.name,
            pod.status.host_ip,
            pod.metadata.labels,
            pod.status.container_statuses[0].container_id[9:]  # Discarding 'docker://'
        )

    @staticmethod
    def decode(o):
        return LitePod(o['name'], o['host_ip'], o['labels'], o['container'])


def is_allowed(route):
    from re import match
    return len(
        list(
            filter(lambda r: match(r, route), ALLOWED_ROUTES)
        )
    ) > 0


def process_file(request, filename):
    if filename in request.files and \
            request.files[filename].filename and \
            request.files[filename].filename.split('.')[-1] in ALLOWED_EXTENSIONS:
        # Save file
        file = request.files[filename]
        location = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(location)
        # Map file to requests
        return location
    return ''


def get_port(pod):
    label = 'io.kompose.service=%s' % pod.labels['io.kompose.service']
    ports = list(filter(
        lambda candidate_port: candidate_port.name == 'serviceport',
        KUBE_API.list_namespaced_service('default', label_selector=label).items[0].spec.ports
    ))
    if not ports:
        app.logger.error("No service available for pod with label %s" % label)
        raise RuntimeError()
    if not ports[0].node_port:
        app.logger.error("Pod with label %s has no externally accessible port - is the service NodePort?" % label)
        raise RuntimeError()
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
                pod.status.container_statuses if pod.status.container_statuses else []
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
            app.logger.info("QoS not found, querying Kubernetes...")
            QOS = get_qos()
            app.logger.info("Done. Retrying request")

    if res.status_code != 200:
        return res.status_code, None
    best_pod = LitePod.decode(res.json())
    return res.status_code, 'D%s:%s' % (best_pod.host_ip, get_port(best_pod))


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def on_request(path):
    app.logger.info("Received request. Method: %s, Route: %s" % (request.method, path))
    time = app.logger.info("Time: ", datetime.utcnow())

    if not path:  # If /, return 200 (for testing)
        stepback_time = timedelta(seconds=10)
        res = requests.get(
            'http://mongoapi:8000/query/performance',
            data=json.dumps({
                'usage.time': {'$gte': (time - stepback_time).isoformat()},
                'container': {'$exists': True},
                '$sort': [('usage.time', 1)]
            }),
            timeout=5 / 2,
            stream=True
        )
        elasticQuery = {"query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "usage.time": {
                                "gte": (time - stepback_time).isoformat()
                            }
                        }
                    },
                    {
                        "exists": {
                            "field": "container"
                        }
                    }
                ]}
        },
            '$sort': [('usage.time', 1)],
            '$test': True
        }
        res = requests.get('http://mongoapi:8000/query/performance', data=json.dumps(elasticQuery),
                           timeout=5 / 2,
                           stream=True)

        f = open("mongo.txt", "w+")
        f.write('\n'.join([json.dumps(measurement) for measurement in JsonStreamIterator(res)]))
        f.close()

        f = open("elastic.txt", "w+")
        f.write('\n'.join([json.dumps(x["_source"]) for x in elasticResponse["hits"]["hits"]]))
        f.close()

        # app.logger.info("MongoAPI: ", [measurement for measurement in JsonStreamIterator(res)])
        # app.logger.info("Elastic: ", [x["_source"] for x in elasticResponse["hits"]["hits"]])
        return ''

    if not is_allowed(path):
        app.logger.info('Unauthorized route')
        abort(401)
        return

    if len(path.split('/')) == 1:
        service, route = path, ''
    else:
        service, route = path.split('/', maxsplit=1)

    params = request.query_string.decode()
    # Get the service related to this path
    mapped_service = ROUTE_MAP[service] if service in ROUTE_MAP else ''
    if not mapped_service:
        app.logger.info('Desired service not in mapping')
        abort(404)
        return

    # Get appropriate worker for service
    app.logger.info("Getting best host for %s" % mapped_service)
    status, host = get_best_host(mapped_service)
    if status != 200:
        abort(status)
        return
    app.logger.info("Got best host: %s" % host)
    url = 'http://%s/%s' % (host, route)

    if params:
        url = url + "?" + params
    # Add files if necessary
    app.logger.info("Processing files")
    files = {}
    for file in POSSIBLE_FILES:
        loc = process_file(request, file)
        if loc:
            files[file] = open(loc, 'rb')

    # Get body
    app.logger.info("Processing body")
    data = json.dumps(request.get_json()) if request.is_json else None

    # Route request
    app.logger.info("Routing %s to %s" % (request.method, url))
    req = requests.request(request.method, url, data=data, files=files)
    app.logger.info("Response received: %d" % req.status_code)

    # Remove files
    for file in POSSIBLE_FILES:
        if file in files:
            os.remove(files[file].name)
    app.logger.info("Cleaned files")

    # Process response
    if req.status_code != 200:
        abort(req.status_code)
        return
    return app.response_class(response=req.content, mimetype='application/json')


if __name__ == '__main__':
    QOS = get_qos()
    app.run(debug=True, host='0.0.0.0')
