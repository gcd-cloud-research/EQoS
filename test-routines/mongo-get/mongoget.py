import requests

res = requests.get('http://mongoapi:8000/query/tasks')
with open('results.json', 'w+') as fh:
    fh.write(res.text)
