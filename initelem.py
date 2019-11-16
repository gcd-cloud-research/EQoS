#!/bin/python

import pymongo
from datetime import datetime

client = pymongo.MongoClient("mongodb://admin:toor@localhost:27017")
result = client.ehqos.tasks.insert_one({
    'status': 'RUNNING',
    'issuer': 'Unknown',
    'start_time': datetime.utcnow().isoformat()
})
print(result.inserted_id)
