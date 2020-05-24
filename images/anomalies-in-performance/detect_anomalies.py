import json
from signal import signal, SIGALRM, alarm, pause
from datetime import datetime, timedelta
import logging

from luminol.anomaly_detector import AnomalyDetector
from luminol.exceptions import NotEnoughDataPoints
import requests
from pymongo import MongoClient

PERFORMANCE_URL = 'http://mongoapi:8000/query/performance'
T = 1 * 60  # Seconds between checks
MONGO_CLIENT = MongoClient("mongodb://admin:toor@internaldb:27017")

class JsonStreamIterator:
    # Does not accept lists as items, as it only needs to process performance objects
    def __init__(self, response):
        self.ite = response.iter_content(decode_unicode=True)

    def __iter__(self):
        return self

    def __next__(self):
        string = ''
        open_count = 0
        for char in self.ite:
            string += char.decode('utf-8')
            if string[-1] == '{':
                open_count += 1
            if string[-1] == '}':
                open_count -= 1
                if not open_count:
                    break
        if not string:
            raise StopIteration()
        return json.loads(string)


def get_data(start_time, is_container=True):
    res = requests.get(PERFORMANCE_URL, data=json.dumps({
        'usage.time': {'$gte': start_time.isoformat()},
        'container': {'$exists': is_container},
        '$sort': [('usage.time', -1)]
    }))
    if res.status_code != 200:
        res.close()
        return {}

    data = {}
    for entry in JsonStreamIterator(res):
        container = entry.pop('container')
        data[container] = data[container] + [entry] if container in data else [entry]
    return data


def upload_anomalies(anom_list):
    if not anom_list:
        return
    insertion = []
    for anom in anom_list:
        insertion.append({
            'time': anom.get_time_window(),
            'score': anom.anomaly_score
        })
    MONGO_CLIENT.ehqos.anomalies.insert_many(insertion)


if __name__ == '__main__':
    def ignore(sig, frame):
        pass
    signal(SIGALRM, ignore)
    while True:
        alarm(T)

        for container, data in get_data(datetime.now() - timedelta(seconds=T)).items():
            cpu = {}
            mem = {}
            for datapoint in data:
                ts = datetime.fromisoformat(datapoint['usage']['time'].split('.')[0]).timestamp()
                cpu[ts] = datapoint['usage']['cpu']
                mem[ts] = datapoint['usage']['memory']

            try:
                container_detector = AnomalyDetector(cpu)
                anomalies = container_detector.get_anomalies()
            except (NotEnoughDataPoints, IndexError):
                anomalies = []
            logging.debug("Detected %d CPU anomalies in container %s" % (len(anomalies), container))
            upload_anomalies(anomalies)

            try:
                container_detector = AnomalyDetector(mem)
                anomalies = container_detector.get_anomalies()
            except (NotEnoughDataPoints, IndexError):
                anomalies = []
            logging.debug("Detected %d memory anomalies in container %s" % (len(anomalies), container))
            upload_anomalies(anomalies)
        pause()
