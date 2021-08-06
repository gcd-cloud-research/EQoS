import json
from signal import signal, SIGALRM, alarm, pause
from datetime import datetime, timedelta
import logging

from luminol.anomaly_detector import AnomalyDetector
from luminol.exceptions import NotEnoughDataPoints
import requests
from pymongo import MongoClient
from elasticsearch import Elasticsearch

T = 1 * 60  # Seconds between checks
MONGO_CLIENT = MongoClient("mongodb://admin:toor@internaldb:27017")
es = Elasticsearch([
    'monitornode.eqos:9200'
])


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
    elasticQuery = {"query": {
        "bool": {
            "must": [
                {
                    "range": {
                        "usage.time": {
                            "gte": start_time.isoformat()
                        }
                    }
                },
                {
                    "exists": {
                        "field": "container" if is_container else "pod"
                    }
                }
            ]}
        },
        '$sort': [('usage.time', -1)]
    }
    query_result = es.search(index="performance", filter_path=['hits.hits._source'],
                             body=elasticQuery, size=1000,
                             sort="usage.time:desc")

    res = [x["_source"] for x in query_result["hits"]["hits"]]

    l_data = {}
    for entry in res:
        l_container = entry.pop('container')
        l_data[l_container] = l_data[l_container] + [entry] if l_container in l_data else [entry]
    return l_data


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
