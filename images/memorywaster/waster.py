import os
import signal
from time import sleep
import logging

import pymongo

logging.basicConfig(level=logging.INFO)
TARGET_LOAD = 80
TOLERANCE = 5


def waster():
    byeMemory = []
    while True:
        global shouldFill
        if shouldFill:
            byeMemory.append([0]*1000)


if __name__ == '__main__':
    with open('hostname') as fh:
        host = fh.readline().strip()

    global shouldFill
    logging.info(host)
    client = pymongo.MongoClient('mongodb://admin:toor@internaldb:27017')
    shouldFill = True
    pids = []

    while True:

        last_perf = None
        while not last_perf:
            try:
                last_perf = list(client.ehqos.performance
                                 .find({'host': host})
                                 .sort([('usage.time', pymongo.DESCENDING)])
                                 .limit(1)
                                 )
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
