import requests
from datetime import datetime
from calendar import timegm

format = "%Y-%m-%dT%H:%M:%S"


def nanosecs(ts):
    whole, decimal = ts.split(".")
    decimal = decimal[:-1]  # Remove final Z
    seconds = timegm(
        datetime.strptime(whole, format).timetuple()
    ) + float("0." + decimal)
    return seconds * 10 ** 9


def display(time, cpu, memory):
    print(time)
    print("\tCPU: %f%%" % (cpu))
    print("\tMem: %.2f%%" % (memory))
    print("")


def get_stats(stats):
    time = stats['timestamp']
    cpu = stats['cpu']['usage']['total']
    mem = stats['memory']['usage']
    return time, cpu, mem


def get_usage():
    try:
        cr = requests.get("http://monitor:8080/api/v1.3/containers")
        cjson = cr.json()
        mr = requests.get("http://monitor:8080/api/v1.3/machine")
        mjson = mr.json()
    except:
        return (0, 100, 100)

    max_mem = mjson['memory_capacity']
    max_cores = mjson['num_cores']
    time, cpu, mem = get_stats(cjson['stats'][-1])
    prev_time, prev_cpu, _ = get_stats(cjson['stats'][-2])
    if time == prev_time:
        return (time, 100, 100)
    cpu_usage = (cpu - prev_cpu) / (nanosecs(time) - nanosecs(prev_time))
    cpu_percent = float(cpu_usage) / float(max_cores) * 100
    mem_percent = float(mem) / float(max_mem) * 100
    return (time, cpu_percent, mem_percent)
