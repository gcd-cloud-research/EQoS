import falcon
import pymongo
import json
import sys
from datetime import datetime
from bson.objectid import ObjectId


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

BUSINESS_CLIENT = pymongo.MongoClient(
    "mongodb://%s:%s@businessdb:27017" %
    (conf['business']['mongo_user'], conf['business']['mongo_pass'])
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
        from datetime import datetime
        print("%s - Received request" % datetime.now().isoformat(), flush=True)
        query = req.media if req.media else {}

        if 'id' in query:
            query['_id'] = ObjectId(query['id'])
            del query['id']

        sort = None
        if '$sort' in query:
            sort = query['$sort']
            del query['$sort']
        if collection in INTERNAL_CLIENT.ehqos.list_collection_names():
            query_result = INTERNAL_CLIENT.ehqos[collection].find(query, limit=100 if not query else 0)
        elif collection in BUSINESS_CLIENT.ehqos.list_collection_names():
            query_result = BUSINESS_CLIENT.ehqos[collection].find(query, limit=100 if not query else 0)
        else:
            resp.status = falcon.HTTP_404
            return
        print("%s - Queried" % datetime.now().isoformat(), flush=True)
        query_result = query_result.sort(sort) if sort else query_result
        print("%s - Sorted" % datetime.now().isoformat(), flush=True)
        resp.stream = map(lambda x: Query.format_elem(x), query_result)
        print("%s - Request completed" % datetime.now().isoformat(), flush=True)

    @staticmethod
    def format_elem(elem):
        elem['id'] = str(elem['_id'])
        del elem['_id']
        return json.dumps(elem).encode('utf-8')

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

        result = BUSINESS_CLIENT.ehqos.tasks.insert_one({
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

        BUSINESS_CLIENT.ehqos.tasks.update_one({"_id": ObjectId(routine_id)}, {"$set": data})


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
        for collection in BUSINESS_CLIENT.ehqos.list_collection_names():
            BUSINESS_CLIENT.ehqos.drop_collection(collection)


api = falcon.API()
testResource = Test()
queryResource = Query()
routineResource = Routine()
performanceResource = Performance()
deleteResource = Delete()
api.add_route('/test', testResource)
api.add_route('/query/{collection}', queryResource)
api.add_route('/query', queryResource, suffix="all")
api.add_route('/routine/new', routineResource, suffix="create")
api.add_route('/routine/{routine_id}', routineResource, suffix="update")
api.add_route('/performance', performanceResource)
api.add_route('/', deleteResource)
