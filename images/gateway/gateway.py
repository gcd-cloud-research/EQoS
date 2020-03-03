import os
import falcon
import json
from http.client import HTTPConnection

DATA_DIR = "/routing/"
HEADERS = {'Content-Type': 'application/json'}


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


def on_request(req, resp):
    try:
        body = json.load(req.bounded_stream)
    except json.JSONDecodeError:
        body = {}

    service = req.relative_uri.split("/")[1]
    uri = "/".join(req.relative_uri.split("/")[2:])

    host = get_best_host(service)
    if host is None:
        resp.status = falcon.HTTP_404
        return

    conn = HTTPConnection(host)
    conn.request(req.method, uri, body, HEADERS)

    response = conn.getresponse()
    print(response.getcode())
    if response.getcode() != 200:
        resp.status = falcon.HTTP_500
        return
    body = response.read().decode('utf-8')
    resp.body = json.dumps(body)


api = falcon.API()
api.add_sink(on_request, '/')