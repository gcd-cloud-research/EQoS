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
    "mongodb://%s:%s@mongo:27017" %
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

        Filters are obtained by combining body and query parameters.
        Query parameters have precedence.
        """
        query = req.media if req.media is not None else {}

        if 'id' in query:
            query['_id'] = ObjectId(query['id'])
            del query['id']

        if collection in CLIENT.ehqos.list_collection_names():
            query_result = CLIENT.ehqos[collection].find(query)
        else:
            resp.status = falcon.HTTP_404
            return

        body = []
        for elem in query_result:
            elem['id'] = str(elem['_id'])
            del elem['_id']
            body.append(elem)
        resp.body = json.dumps(body)

    def on_get_all(self, req, resp):
        """Return all available collections."""
        resp.body = json.dumps(CLIENT.ehqos.list_collection_names())


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
    def on_post(self, req, resp):
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
api.add_route('/delete', deleteResource)
