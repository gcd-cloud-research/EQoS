#!/bin/python

import pymongo
from datetime import datetime
import sys
import json
import os

LOG = "log.log"
RES = "results.json"

def exists(path):
    import os
    return os.path.isfile("./" + path)

# Get routine id
if not exists("id.txt"):
    sys.exit(1)

with open("id.txt") as fh:
    from bson.objectid import ObjectId
    id = ObjectId(fh.readline().strip())

# Run routine
if os.fork() == 0:
    os.execlp('python', '-u', '/worker.py')
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
client = pymongo.MongoClient("mongodb://admin:toor@mongo:27017")
client.ehqos.tasks.update_one({"_id": id}, {"$set": {
    'status': 'SUCCESS' if status == 0 else 'FAILURE',
    'end_time': datetime.utcnow().isoformat(),
    'logs': log,
    'results': results
}})
