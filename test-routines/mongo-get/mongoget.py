import requests
import json
from datetime import datetime, timedelta
res = requests.get('http://mongoapi:8000/query/performance', data=json.dumps({
    'usage.time': {'$lte': (datetime.utcnow()).isoformat()},
    '$sort': [('usage.time', -1)]
}))
with open('results.json', 'w+') as fh:
    fh.write(json.dumps({'fetched': len(res.json())}))
