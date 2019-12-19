#!/bin/python

import pymongo
from datetime import datetime
import sys
import json
import os
from bson.objectid import ObjectId

CONF = "config.json"
LOG = "log.log"
RES = "results.json"

def exists(path):
    return os.path.isfile("./" + path)

# Get configuration
if (not exists(CONF)):
    sys.exit(1)

with open(CONF) as fh:
    conf = json.load(fh)
    if 'mongo_user' not in conf or 'mongo_pass' not in conf:
        sys.exit(1)

id = ObjectId(sys.argv[1])

# Set routine as RUNNING
client = pymongo.MongoClient(
    "mongodb://%s:%s@mongo:27017" % (conf['mongo_user'], conf['mongo_pass'])
)
client.ehqos.tasks.update_one({"_id": id}, {"$set": {
    'status': 'RUNNING'
}})

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
client.ehqos.tasks.update_one({"_id": id}, {"$set": {
    'status': 'SUCCESS' if status == 0 else 'FAILURE',
    'end_time': datetime.utcnow().isoformat(),
    'logs': log,
    'results': results
}})
