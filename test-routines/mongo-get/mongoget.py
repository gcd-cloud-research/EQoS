import pymongo
import json

client = pymongo.MongoClient('mongodb://%s:%s@businessdb:27017' % ('admin', 'toor'))

with open('results.json', 'w+') as fh:
    fh.write(json.dumps(client.test.random.find()[0]))
