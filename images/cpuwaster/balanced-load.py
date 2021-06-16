import os
import signal
from time import sleep
import logging
from elasticsearch import Elasticsearch

import pymongo

logging.basicConfig(level=logging.INFO)
TARGET_LOAD = 90
TOLERANCE = 5

es = Elasticsearch([
    'monitornode.eqos:9200'
])

def waster():
    i = 0
    while True:
        i += 1
        i -= 1


if __name__ == '__main__':
    with open('hostname') as fh:
        host = fh.readline().strip()
    logging.info(host)
    client = pymongo.MongoClient('mongodb://admin:toor@internaldb:27017')
    pids = []
    while True:
        elasticQuery = {
            "query": {
                "match": {
                    "host": host
                }
            }
        }

        query_result = es.search(index="performance", filter_path=['hits.hits._source'],
                                 body=elasticQuery, size=1,
                                 sort="usage.time:desc")

        last_perf = [x["_source"] for x in query_result["hits"]["hits"]]
        last_perf = last_perf[0] if len(last_perf) > 0 else None

        cpu = last_perf['usage']['cpu']
        if cpu >= 100:
            logging.info(cpu)
        if cpu < TARGET_LOAD - TOLERANCE:
            pid = os.fork()
            if pid == 0:
                waster()
                exit(1)
            pids.append(pid)
            logging.info('Scaled %d' % len(pids))
        elif cpu > TARGET_LOAD + TOLERANCE:
            if not pids:
                logging.warning('Should remove a child, but none are available')
            else:
                victim = pids.pop()
                os.kill(victim, signal.SIGTERM)
                os.waitpid(victim, 0)
                logging.info('Descaled %d' % len(pids))
        else:
            logging.info("CPU is in ideal load")
        sleep(5)
