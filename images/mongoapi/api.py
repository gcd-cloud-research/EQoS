import falcon
import pymongo
import json
import sys
from datetime import datetime
from bson.objectid import ObjectId
import logging

logging.basicConfig(level=logging.DEBUG)

JSON_CONF_STRUCTURE = {  # '{}' represents a value
        'internal': {'mongo_user': {}, 'mongo_pass': {}},
        'business': {'mongo_user': {}, 'mongo_pass': {}}
    }


def valid_conf(reference, conf_obj):
    for key in reference.keys():
        if key not in conf_obj or not valid_conf(reference[key], conf_obj[key]):
            return False
    return True


with open("config.json") as fh:
    conf = json.load(fh)
    if not valid_conf(JSON_CONF_STRUCTURE, conf):
        sys.exit(1)


INTERNAL_CLIENT = pymongo.MongoClient(
    "mongodb://%s:%s@internaldb:27017" %
    (conf['internal']['mongo_user'], conf['internal']['mongo_pass'])
)


class Test:
    """Endpoint for checking that service is up."""

    def on_get(self, req, resp):
        return


class Query:
    """Process queries to MongoDB database."""

    def on_get(self, req, resp, collection):
        """
        Return results from given collection with given filters.

        Filters are obtained by body parameters.
        """
        query = req.media if req.media else {}

        if 'ids' in query:
            ids = query.pop('ids')
            query["_id"] = {"$in": [ObjectId(x) for x in ids]}

        if 'id' in query:
            query['_id'] = ObjectId(query.pop('id'))

        stream = collection == 'performance'
        if 'stream' in query:
            stream = query.pop('stream')

        sort = None
        if '$sort' in query:
            sort = query.pop('$sort')

        limit = 0
        if '$limit' in query:
            limit = query.pop('$limit')

        if collection in INTERNAL_CLIENT.ehqos.list_collection_names():
            query_result = INTERNAL_CLIENT.ehqos[collection].find(query, limit=limit)
        else:
            resp.status = falcon.HTTP_404
            return

        query_result = query_result.sort(sort) if sort else query_result
        query_result = map(lambda x: Query.format_id(x), query_result)
        if stream:
            resp.stream = map(lambda x: json.dumps(x).encode('utf-8'), query_result)
        else:
            resp.body = json.dumps(list(query_result))

    @staticmethod
    def format_id(elem):
        elem['id'] = str(elem.pop('_id'))
        return elem

    def on_get_all(self, req, resp):
        """Return all available collections."""
        resp.body = json.dumps(INTERNAL_CLIENT.ehqos.list_collection_names())

    def on_post_all(self, req, resp):
        """Bulk upload into an existing or new collection."""
        if not req.media:
            resp.status = falcon.HTTP_400
            resp.body = 'Request body required'
            return

        if 'collection' not in req.media or 'data' not in req.media:
            resp.status = falcon.HTTP_400
            resp.body = 'Request body must contain keys "collection" and "data"'
            return

        col, data = req.media['collection'], req.media['data']
        INTERNAL_CLIENT.ehqos[col].insert_many(data)


class Routine:
    def on_post_create(self, req, resp):
        data = req.media
        if data is None:
            resp.status = falcon.HTTP_400
            return

        result = INTERNAL_CLIENT.ehqos.tasks.insert_one({
            'name': data["name"],
            'status': 'PENDING',
            'issuer': data["issuer"],
            'start_time': datetime.utcnow().isoformat()
        })
        resp.body = json.dumps({"id": str(result.inserted_id)})

    def on_post_update(self, req, resp, routine_id):
        data = req.media
        if data is None:
            resp.status = falcon.HTTP_400
            return

        if data['status'] == 'SUCCESS' or data["status"] == 'FAILURE':
            data['end_time'] = datetime.utcnow().isoformat()

        INTERNAL_CLIENT.ehqos.tasks.update_one({"_id": ObjectId(routine_id)}, {"$set": data})


class Performance:
    def on_post(self, req, resp):
        data = req.media
        if data is None:
            resp.status = falcon.HTTP_400
            return

        INTERNAL_CLIENT.ehqos.performance.insert_many(data)


class Delete:
    def on_delete(self, req, resp):
        for collection in INTERNAL_CLIENT.ehqos.list_collection_names():
            INTERNAL_CLIENT.ehqos.drop_collection(collection)


class TaskPerformance:
    """Retrieves all the performance metrics for a """

    def on_get(self, req, resp):
        """
        Return results from given collection with given filters.

        Filters are obtained by body parameters.
        """
        query = req.media if req.media else {}

        if 'id' in query:
            id = query.pop('id')
            query['_id'] = ObjectId(id) if type(id) == str else {"$in": [ObjectId(x) for x in id]}

        tasks_query = INTERNAL_CLIENT.ehqos['tasks'].find(query, {"_id": 1, "status": 1, "start_time": 1, "end_time": 1})
        tasks_list = list(map(lambda x: Query.format_id(x), tasks_query))
        result = {}
        for task in tasks_list:
            start_time = task["start_time"]
            end_time = task["end_time"]
            performance_query = INTERNAL_CLIENT.ehqos['performance'].find(
                {"usage.time": {"$gt": start_time, "$lt": end_time}}
            )

            performance_query = map(lambda x: Query.format_id(x), performance_query)
            result[task["id"]] = list(performance_query)

        resp.body = json.dumps(result)


api = falcon.API()
testResource = Test()
queryResource = Query()
routineResource = Routine()
performanceResource = Performance()
taskperformanceResource = TaskPerformance()
deleteResource = Delete()
api.add_route('/test', testResource)
api.add_route('/query/{collection}', queryResource)
api.add_route('/query', queryResource, suffix="all")
api.add_route('/routine/new', routineResource, suffix="create")
api.add_route('/routine/{routine_id}', routineResource, suffix="update")
api.add_route('/performance', performanceResource)
api.add_route('/taskperformance', taskperformanceResource)
api.add_route('/', deleteResource)
