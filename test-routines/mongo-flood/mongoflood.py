import os
import logging
import random

from pymongo import MongoClient, DESCENDING

PROCESSES = 100
REQUESTS = 100
logging.basicConfig(level=logging.WARNING, format='PID %(process)d - %(levelname)s: %(message)s')


children = []
for _ in range(PROCESSES):
    pid = os.fork()
    if not pid:
        random.seed(os.getpid())
        client = MongoClient('mongodb://admin:toor@externaldb:27017')
        for i in range(REQUESTS):
            try:
                logging.info('Requesting %d' % i)
                client.test.random.find().sort('test1', DESCENDING)
                client.test.random.find({'test2': {'$gte': 0}, 'test4': {'$lte': 0}}).sort('test1', DESCENDING)
                client.test.random.update_many({'test0': {'$lt': 0}}, {'$set': {'test0': random.randint(-10000, 0)}})
                logging.info('Request %d successful.' % i)
            except:
                logging.error('Error on request')
        exit(0)
    children.append(pid)
for pid in children:
    os.waitpid(pid, 0)
logging.info("Finished successfully")
