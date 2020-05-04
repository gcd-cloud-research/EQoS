import os

import requests
import json
from datetime import datetime, timedelta

with open('results.json', 'w+') as fh:
    fh.write('[')

for _ in range(200):
    if os.fork() == 0:
        res = requests.get('http://mongoapi:8000/query/performance', data=json.dumps({
            'usage.time': {'$lte': (datetime.utcnow()).isoformat()},
            '$sort': [('usage.time', -1)]
        }))
        with open('results.json', 'a') as fh:
            fh.write('%d,' % len(res.json()) if res.status_code != 200 else 0)

fh.write(']')
