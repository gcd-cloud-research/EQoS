""""This service runs outside of the cluster on net=host or a mapped port."""
from flask import Flask, request, abort
import requests
import re
from kubernetes import client, config

config.load_kube_config()  # TODO: give the gateway the appropriate files to authenticate itself
kube_api = client.ApiClient()

ROUTE_MAP = {
    'mongo': 'mongoapi',
    'routine': 'producer'
}

ALLOWED_ROUTES = [
    r'^/mongo/query',
    r'^/routine$'
]


def is_allowed(route):
    return len(
        list(
            filter(lambda r: re.match(r, route), ALLOWED_ROUTES)
        )
    ) > 0


def get_best_host(service_name):
    """Request best worker (host:port) to QoS service."""
    res = requests.get('/qos:8000/worker?service=%s' % service_name)
    if res.status_code != 200:
        return res.status_code, None

    j = res.json()
    return res.status_code, '%s:%s' % (j['host'], j['port'])


app = Flask(__name__)


@app.route('/')
def on_request():
    # Get desired service
    service = request.script_root
    mapped_service = ROUTE_MAP[service] if service in ROUTE_MAP else ''

    if mapped_service == '':
        return

    if not is_allowed(request.path):
        abort(401)
        return

    # Get appropriate worker for service
    status, host = get_best_host(mapped_service)
    if status != 200:
        abort(status)
        return

    # Add files if necessary
    files = {}
    if 'program' in request.files:
        files['program'] = request.files['program']

    # Route request
    req = requests.request(request.method, 'http://' + host + request.full_path, data=request.get_json(), files=files)

    # Process response
    return req.json()


app.run(debug=False, host='0.0.0.0')