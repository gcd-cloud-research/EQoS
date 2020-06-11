import json
import os
import logging
import random
import time

from pymongo import MongoClient, DESCENDING
import requests

OVERLOAD = 60
PERFORMANCE_URL = 'http://mongoapi:8000/query/performance'
logging.basicConfig(level=logging.WARNING, format='PID %(process)d - %(levelname)s: %(message)s')


def create_child():
    if not os.fork():
        random.seed(os.getpid())
        client = MongoClient('mongodb://admin:toor@businessdb:27017')
        while True:
            try:
                client.test.random.find().sort('test1', DESCENDING)
                client.test.random.find({'test2': {'$gte': 0}, 'test4': {'$lte': 0}}).sort('test1', DESCENDING)
                client.test.random.update_many({'test0': {'$lt': 0}}, {'$set': {'test0': random.randint(-10000, 0)}})
            except Exception as e:
                logging.error('Error on request: %s' % e)


done = False
while not done:
    try:
        res = requests.get(
            PERFORMANCE_URL,
            data=json.dumps({
                'pod': {'$regex': 'businessdb'},
                '$sort': [['usage.time', -1]],
                '$limit': 1,
                'stream': 0
            })
        )
    except:
        logging.warning('Error making request')
        time.sleep(1)
        continue
    if res.status_code != 200:
        logging.warning('Received code %d' % res.status_code)
        time.sleep(1)
        continue
    measurement = res.json()[0]['usage']
    if max(measurement['cpu'], measurement['memory']) > OVERLOAD:
        logging.info('Overload achieved')
        done = True
    else:
        logging.info('Creating new child')
        create_child()
        time.sleep(10)

time.sleep(60)
logging.info("Finished successfully")
