#!/bin/python

from http.client import HTTPConnection
import sys
import json
import os


def exists(path):
    return os.path.isfile("./" + path)


LOG = "log.log"
RES = "results.json"
headers = {'Content-Type': 'application/json'}
conn = HTTPConnection('mongoapi:8000')


routine_id = sys.argv[1]

# Set routine as RUNNING
conn.request('POST', '/routine' + routine_id, json.dumps({'status': 'RUNNING'}), headers)

# Run routine
extension = sys.argv[2]
if os.fork() == 0:
    if extension == 'py':
        os.execlp('python', '-u', '/worker.py')
    elif extension == 'r':
        os.execlp('Rscript', '/worker.r')
_, status = os.wait()

# Get results from files
log = {}
results = {}
if exists(LOG):
    with open(LOG) as fh:
        for line in fh:
            split = line.split("-")
            log[split[0].strip()] = log[split[1].strip()]

if exists(RES):
    with open(RES) as fh:
        results = json.load(fh)

# Save results in database
conn.request('POST', '/routine' + routine_id, json.dumps({
    'status': 'SUCCESS' if status == 0 else 'FAILURE',
    'logs': log,
    'results': results
}), headers)
