import json
from datetime import datetime, timedelta
import logging

import falcon
import requests
from kubernetes import client, config
from elasticsearch import Elasticsearch

logging.basicConfig(level=logging.DEBUG)

# config.load_incluster_config()
KUBE_API = client.CoreV1Api()

LOAD_CHECKING_INTERVAL = 3 * 60  # Amount of seconds to go back when averaging load for choosing least busy container
SYSTEM_LOAD_BACKTRACKING_TIME = 10  # Small amount, but enough to make sure we get data of all hosts
JOB_CREATION_THRESHOLD = 80
PERFORMANCE_URL = 'http://mongoapi:8000/query/performance'

es = Elasticsearch([
    'monitornode.eqos:9200'
])


def add_dicts(dict1, dict2):
    if dict1.keys() != dict2.keys():
        raise ValueError("Dicts don't have the same keys")
    result = {}
    for key in dict1.keys():
        result[key] = dict1[key] + dict2[key]
    return result


def get_elastic_data(query_time, container=None, host=None):
    elasticQuery = {
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "usage.time": {
                                "gte": query_time
                            }
                        }
                    }
                ]}
        }
    }

    if container:
        elasticQuery["query"]["bool"]["filter"] = {
            "terms": {
                "container": container
            }
        }

    if host:
        elasticQuery["query"]["bool"]["must"].append({
            "exists": {
                "field": "host"
            }
        })

    query_result = es.search(index="performance",
                             body=elasticQuery, size=1000,
                             sort="usage.time:desc")

    return [x["_source"] for x in query_result["hits"]["hits"] if "_source" in x]


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


class Test:
    def on_get(self, req, resp):
        return


class Worker:
    def on_get(self, req, resp):
        pods = req.media
        if not pods:
            resp.status = falcon.HTTP_400
            resp.body = 'Body should contain pod objects'
            return

        container_names = list(map(lambda pod: pod['container'], pods))
        logging.debug("Querying for pods %s" % container_names)
        # Get worker performance
        res = get_elastic_data(datetime.utcnow() - timedelta(seconds=LOAD_CHECKING_INTERVAL),
                               container=container_names)

        # Aggregate performances for each container
        performance = {}
        for entry in res:
            if not entry:
                continue

            logging.debug(entry)
            container = entry['container']
            if container not in performance:
                performance[container] = {'cpu': 0, 'memory': 0, 'count': 0}
            performance[container]['cpu'] += entry['usage']['cpu']
            performance[container]['memory'] += entry['usage']['memory']
            performance[container]['count'] += 1

        # If there is no data, return first pod
        if not performance:
            resp.body = json.dumps(pods[0])
            return

        # Average CPU and memory load
        for perf in performance.values():
            perf['cpu'] /= perf['count']
            perf['memory'] /= perf['count']
            del perf['count']

        # The selection could be better if the QoS knew whether the job is CPU or memory intensive.
        # Currently, selection takes place by averaging CPU and memory load and taking the lowest.
        # Thus, it is assumed that CPU and memory have the same weight in the selection.
        containers = performance.items()
        logging.debug("Containers: %s" % containers)
        selected_container = min(performance.items(), key=lambda tup: tup[1]['cpu'] + tup[1]['memory'] / 2)[0]
        resp.body = json.dumps(list(filter(lambda pod: pod['container'] == selected_container, pods))[0])


class SystemLoad:
    def on_get(self, req, resp):
        res = get_elastic_data((datetime.utcnow() - timedelta(seconds=SYSTEM_LOAD_BACKTRACKING_TIME)).isoformat(), host=True)

        can_run_job = True
        included_hosts = []
        host_usages = []

        # Last usage of each host
        for entry in res:
            if entry['host'] not in included_hosts:
                del entry['usage']['time']
                host_usages.append(entry['usage'])
                included_hosts.append(entry['host'])

        if len(host_usages) == 0:
            resp.body = json.dumps({'status': False})
            return

        # Average usages
        from functools import reduce
        logging.debug("Dicts: %s" % add_dicts)
        logging.debug("Hosts: %s" % host_usages)
        accums = reduce(add_dicts, host_usages)
        for value in accums.values():
            if value / len(included_hosts) > JOB_CREATION_THRESHOLD:
                can_run_job = False

        resp.body = json.dumps({'status': can_run_job})


api = falcon.API()
workerResource = Worker()
systemLoadResource = SystemLoad()
api.add_route('/test', Test())
api.add_route('/worker', workerResource)
api.add_route('/sysload', systemLoadResource)
