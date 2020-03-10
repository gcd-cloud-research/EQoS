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
        body = req.media
        query_params = json.loads(body if body else "{}")
        for key, value in req.params.items():
            query_params[key] = value

        if 'id' in query_params:
            query_params['_id'] = ObjectId(query_params['id'])
            del query_params['id']

        if collection in CLIENT.ehqos.list_collection_names():
            query_result = CLIENT.ehqos[collection].find(query_params)
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


api = falcon.API()
testResource = Test()
queryResource = Query()
routineResource = Routine()
performanceResource = Performance()
api.add_route('/test', testResource)
api.add_route('/query/{collection}', queryResource)
api.add_route('/query', queryResource, suffix="all")
api.add_route('/routine/new', routineResource, suffix="create")
api.add_route('/routine/{routine_id}', routineResource, suffix="update")
api.add_route('/performance', performanceResource)
