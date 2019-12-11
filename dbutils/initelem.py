#!/bin/python

import pymongo
from datetime import datetime
import sys
import json
from os import path

if not path.isfile(sys.argv[2]):
    print("Config file not found")
    sys.exit(1)

with open(sys.argv[2]) as fh:
    conf = json.load(fh)
    if 'mongo_user' not in conf or 'mongo_pass' not in conf:
        sys.exit(1)

client = pymongo.MongoClient(
    "mongodb://%s:%s@localhost:27017" %
    (conf['mongo_user'], conf['mongo_pass'])
)
result = client.ehqos.tasks.insert_one({
    'name': sys.argv[1],
    'status': 'PENDING',
    'issuer': 'Unknown',
    'start_time': datetime.utcnow().isoformat()
})
print(result.inserted_id)
