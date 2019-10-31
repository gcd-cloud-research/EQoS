import requests
import time as t
from datetime import datetime
from calendar import timegm

format = "%Y-%m-%dT%H:%M:%S"

def nanosecs(ts):
    whole, decimal = ts.split(".")
    decimal = decimal[:-1]  # Remove final Z
    seconds = timegm(datetime.strptime(whole, format).timetuple()) + float("0." + decimal)
    return seconds * 10 ** 9

def display(time, cpu, memory):
    print(time)
    print("\tCPU: %f%%" % (cpu))
    print("\tMem: %.2f%%" % (memory))
    print("")

previous = None
while(True):
    t.sleep(1)
    try:
        cr = requests.get("http://monitor:8080/api/v1.3/containers")
        cjson = cr.json()
        mr = requests.get("http://monitor:8080/api/v1.3/machine")
        mjson = mr.json()
    except:
        print("Could not connect")
        continue

    totalmem = mjson['memory_capacity']

    time = cjson['stats'][-1]['timestamp']
    cpu = cjson['stats'][-1]['cpu']['usage']['total']
    mem = cjson['stats'][-1]['memory']['usage']
    if previous:
        prev_time, prev_cpu, prev_mem = previous
        if time == prev_time:
            continue
        cpu_usage = (cpu - prev_cpu) / (nanosecs(time) - nanosecs(prev_time))
        display(time, cpu_usage, float(mem) / float(totalmem) * 100)

    previous = (time, cpu, mem)

"""
previous = {}

while(True):
    t.sleep(1)
    try:
        cr = requests.get("http://monitor:8080/api/v1.3/docker")
        cjson = cr.json()
        mr = requests.get("http://monitor:8080/api/v1.3/machine")
        mjson = mr.json()
    except:
        print("Could not connect")
        continue

    totalmem = mjson['memory_capacity']

    for name, info in cjson.items():
        time = info['stats'][-1]['timestamp']
        cpu = info['stats'][-1]['cpu']['usage']['total']
        mem = info['spec']['memory']['limit']
        if name in previous:
            prev_time, prev_cpu, prev_mem = previous[name]
            if time == prev_time:
                continue
            cpu_usage = (cpu - prev_cpu) / nanosecs(prev_time, time)
            print(name, time)
            print("\tMem: %s/%s (%.2f%%)" % (
                mem,
                totalmem,
                float(mem) / float(totalmem)
            ))
            print("\tCPU: %f%%" % (cpu_usage))
        previous[name] = (time, cpu, mem)
"""
