import os
from flask import Flask, request, abort
import requests
import re

DATA_DIR = "/routing/"

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


def parse_host(host_line):
    parts = host_line.split()
    host = parts[0]
    port = parts[1].split("/")[0]
    return "%s:%s" % (host, port)


def get_best_host(service_name):
    candidates = list(filter(lambda candidate: service_name in candidate, os.listdir(DATA_DIR)))
    if len(candidates) == 0:
        return None
    best = candidates[0]

    with open(DATA_DIR + best) as fh:
        best_host = parse_host(fh.read())
    return best_host


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
    host = get_best_host(mapped_service)
    if host is None:
        abort(503)
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