import requests
import time

while(True):
    time.sleep(1)
    try:
        cr = requests.get("http://monitor:8080/api/v1.3/docker")
        cjson = cr.json()
        mr = requests.get("http://monitor:8080/api/v1.3/machine")
        mjson = mr.json()
    except:
        print("Could not connect")
        continue

    totalmem = mjson['memory_capacity']

    for container_name, container_info in cjson.items():
        print(container_name)
        mem = container_info['spec']['memory']['limit']
        print("\tMem: %s/%s (%.2f%%)" % (
            mem,
            totalmem,
            float(mem) / float(totalmem)
        ))
        print("\tCPU: %s" % (container_info['stats'][-1]['cpu']['usage']['total']))
