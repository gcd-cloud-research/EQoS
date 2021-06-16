import os
import signal
from time import sleep
import logging
from elasticsearch import Elasticsearch

import pymongo

logging.basicConfig(level=logging.INFO)
TARGET_LOAD = 80
TOLERANCE = 5

es = Elasticsearch([
    'monitornode.eqos:9200'
])


def waster():
    byeMemory = []
    while True:
        global shouldFill
        if shouldFill:
            byeMemory.append([0]*100000)


if __name__ == '__main__':
    with open('hostname') as fh:
        host = fh.readline().strip()

    global shouldFill
    logging.info(host)
    shouldFill = True
    pids = []

    while True:

        last_perf = None
        while not last_perf:
            try:
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
            except Exception:
                logging.error("Status update failed")

        memory = last_perf['usage']['memory']
        if memory >= 100:
            logging.info(memory)
        if memory < TARGET_LOAD - TOLERANCE:
            pid = os.fork()
            if pid == 0:
                waster()
                exit(1)
            pids.append(pid)
            logging.info('Scaled %d' % len(pids))

        elif memory > TARGET_LOAD + TOLERANCE:
            if not pids:
                logging.warning('Should remove a child, but none are available')
            else:
                victim = pids.pop()
                os.kill(victim, signal.SIGTERM)
                os.waitpid(victim, 0)
                logging.info('Descaled %d' % len(pids))
        else:
            logging.info("Memory is in ideal load")
        sleep(5)
