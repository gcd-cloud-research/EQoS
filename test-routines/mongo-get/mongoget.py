import requests
import json
from datetime import datetime, timedelta
res = requests.get('http://mongoapi:8000/query/performance', data=json.dumps({
    'usage.time': {'$gte': (datetime.utcnow() - timedelta(minutes=5)).isoformat()},
    'container': {'$in': ['f1d1e58ca6907972cd9dd40d264d9327422019f47bc13e26dfa511ef1d4fc0fe', '883a2247cf8a8933d6b25f304640a2a7146e1869d07daec18db63a20a9835edc']},
    '$sort': [('usage.time', -1)]
}))
with open('results.json', 'w+') as fh:
    fh.write(res.text)
