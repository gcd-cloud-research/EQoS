#!/bin/python3

import sys
import json
import os
import logging
import requests
import pymongo
from bson.objectid import ObjectId
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

def exists(path):
    return os.path.isfile("./" + path)


byPassQos = True
LOG = "log.log"
RES = "results.json"

if byPassQos:
    INTERNAL_CLIENT = pymongo.MongoClient(
        'mongodb://%s:%s@internaldb:27017' % ('admin', 'toor')
    )
else:
    URL = 'http://mongoapi:8000/routine/' + sys.argv[1]

routine_id = sys.argv[1]

# Set routine as RUNNING
logging.debug("Starting...")

if byPassQos:
    INTERNAL_CLIENT.ehqos.tasks.update_one({"_id": ObjectId(routine_id)}, {"$set": {'status': 'RUNNING'}})
else:
    requests.post(URL, data=json.dumps({'status': 'RUNNING'}))

logging.debug("Routine set as RUNNING")

# Run routine
logging.debug("Starting routine")
extension = sys.argv[2]
if os.fork() == 0:
    log_fh = open(LOG, 'w+')
    os.dup2(log_fh.fileno(), 1)
    os.dup2(log_fh.fileno(), 2)
    if extension == 'py':
        os.execlp('python3', '-u', '/worker.py')
    elif extension == 'r':
        os.execlp('Rscript', '/worker.r')
_, status = os.wait()
logging.debug("Routine completed. Status code: %d" % status)

# Get results from files
logging.debug("Getting results and log")
log = []
with open(LOG) as fh:
    for line in fh:
        log.append(line.strip())

results = {}
if exists(RES):
    with open(RES) as fh:
        results = json.load(fh)

logging.debug("Saving to database")
# Save results in database

if byPassQos:
    INTERNAL_CLIENT.ehqos.tasks.update_one({"_id": ObjectId(routine_id)}, {"$set": {
        'status': 'SUCCESS' if status == 0 else 'FAILURE',
        'logs': log,
        'results': results,
        'end_time': datetime.utcnow().isoformat()
    }})
else:
    requests.post(URL, data=json.dumps({
        'status': 'SUCCESS' if status == 0 else 'FAILURE',
        'logs': log,
        'results': results
    }))

logging.debug("Completed")
