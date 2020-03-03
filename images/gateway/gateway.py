import os
import falcon
import json
from http.client import HTTPConnection

DATA_DIR = "/routing"
HEADERS = {'Content-Type': 'application/json'}


def get_best_host(service_name):
    candidates = filter(lambda candidate: service_name in candidate, os.listdir(DATA_DIR))
    print(list(candidates))
    if len(list(candidates)) == 0:
        return None

    best = list(candidates)[0]
    with open(best) as fh:
        best_host = fh.readline()
    return best_host


def on_mongoapi(req, resp):
    try:
        body = json.load(req.bounded_stream)
    except json.JSONDecodeError:
        body = {}

    host = get_best_host('mongoapi')
    if host is None:
        return falcon.HTTP_404

    conn = HTTPConnection(host)
    conn.request(req.method, req.relative_uri, body, HEADERS)
    response = conn.getresponse()
    if response.getcode() != 200:
        resp.status = falcon.HTTP_500
        return
    body = response.read().decode('utf-8')
    resp.body = body


api = falcon.API()
api.add_sink(on_mongoapi, '/mongoapi/')