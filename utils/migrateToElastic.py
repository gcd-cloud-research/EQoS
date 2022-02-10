import logging
import pymongo
from elasticsearch import Elasticsearch, helpers
from datetime import datetime
import time

es = Elasticsearch([
    'elastic:9200'
])

INTERNAL_CLIENT = pymongo.MongoClient(
    "mongodb://user:pass@192.168.101.103:27017"
)

try:
    res = es.index(index="test", doc_type="string", body={"topic": "testing", "dataString": "ttest", "timestamp": datetime.utcnow()})
    print(res['result'])
except Exception as error:
    logging.debug(error)
    pass


def format_id(elem):
    elem['id'] = str(elem.pop('_id'))
    return elem


def getallMongoData():
    result = INTERNAL_CLIENT.ehqos['performance'].find({})
    return list(result)


def insertToElastic(data):
    data = getallMongoData()
    print(len(data))

    body = []
    for i in range(len(data)):
        entry = data[i]

        id = entry.pop('_id')
        body.append({
            "_id": str(id),
            "doc_type": "performance",
            "doc": entry
        })
        print(entry)
        if i % 50000 == 0:
            print("Bulking %d" % i)
            response = helpers.bulk(es, body, index='performance')
            print("Done %d" % i)
            body = []

    print("Bulking")
    response = helpers.bulk(es, body, index='performance')
    print("Done")


def testPerformance(timestamp):
    elasticTime = time.time()
    res = es.search(index="performance",   filter_path=['hits.hits._source'], body={"query": {"range": {
      "usage.time": {
        "gte": timestamp
      }}}})

    elasticTime = time.time() - elasticTime
    print(res)
    print("Elastic time: " + str(elasticTime))
    print("ok")
    return [x["_source"] for x in res["hits"]["hits"]]


testPerformance("2021-04-19T10:48:04.326004676Z")

#insertToElastic(getallMongoData())
