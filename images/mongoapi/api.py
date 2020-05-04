import falcon
import pymongo
import json
import sys
from datetime import datetime
from bson.objectid import ObjectId

with open("config.json") as fh:
    conf = json.load(fh)
    if 'mongo_user' not in conf or 'mongo_pass' not in conf:
        sys.exit(1)


CLIENT = pymongo.MongoClient(
    "mongodb://%s:%s@internaldb:27017" %
    (conf['mongo_user'], conf['mongo_pass'])
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

        if 'id' in query:
            query['_id'] = ObjectId(query['id'])
            del query['id']

        sort = None
        if '$sort' in query:
            sort = query['$sort']
            del query['$sort']

        if collection in CLIENT.ehqos.list_collection_names():
            query_result = CLIENT.ehqos[collection].find(query, limit=100 if not query else 0)
        else:
            resp.status = falcon.HTTP_404
            return

        query_result = query_result.sort(sort) if sort else query_result

        body = []
        for elem in query_result:
            elem['id'] = str(elem['_id'])
            del elem['_id']
            body.append(elem)
        resp.body = json.dumps(body)

    def on_get_all(self, req, resp):
        """Return all available collections."""
        resp.body = json.dumps(CLIENT.ehqos.list_collection_names())

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
        CLIENT.ehqos[col].insert_many(data)


class Routine:
    def on_post_create(self, req, resp):
        data = req.media
        if data is None:
            resp.status = falcon.HTTP_400
            return

        result = CLIENT.ehqos.tasks.insert_one({
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

        CLIENT.ehqos.tasks.update_one({"_id": ObjectId(routine_id)}, {"$set": data})


class Performance:
    def on_post(self, req, resp):
        data = req.media
        if data is None:
            resp.status = falcon.HTTP_400
            return

        CLIENT.ehqos.performance.insert_many(data)


class Delete:
    def on_delete(self, req, resp):
        for collection in CLIENT.ehqos.list_collection_names():
            CLIENT.ehqos.drop_collection(collection)


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
