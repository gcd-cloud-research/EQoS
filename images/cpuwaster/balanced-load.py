import os
import signal
from time import sleep
import logging

import pymongo

logging.basicConfig(level=logging.INFO)
TARGET_LOAD = 90
TOLERANCE = 5


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
        last_perf = list(client.ehqos.performance
                         .find({'host': host})
                         .sort([('usage.time', pymongo.DESCENDING)])
                         .limit(1)
                         )[0]
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
