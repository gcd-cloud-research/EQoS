#!/bin/python3

import sys
import json
import os
import requests


def exists(path):
    return os.path.isfile("./" + path)


LOG = "log.log"
RES = "results.json"
URL = 'http://mongoapi:8000/routine/' + sys.argv[1]

# Set routine as RUNNING
requests.post(URL, data=json.dumps({'status': 'RUNNING'}))

# Run routine
extension = sys.argv[2]
if os.fork() == 0:
    if extension == 'py':
        os.execlp('python3', '-u', '/worker.py')
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
requests.post(URL, data=json.dumps({
    'status': 'SUCCESS' if status == 0 else 'FAILURE',
    'logs': log,
    'results': results
}))
