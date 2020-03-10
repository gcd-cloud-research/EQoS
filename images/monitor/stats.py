#!/usr/bin/python3
from datetime import datetime
from calendar import timegm
import requests


def nanosecs(ts):
    """Convert timestamp to its equivalent in nanoseconds"""
    whole, decimal = ts.split(".")
    decimal = decimal[:-1]  # Remove final Z
    seconds = timegm(
        datetime.strptime(whole, "%Y-%m-%dT%H:%M:%S").timetuple()
    ) + float("0." + decimal)
    return seconds * 10 ** 9


def get_stats(stats):
    return stats['timestamp'], stats['cpu']['usage']['total'], stats['memory']['usage']


def get_usage(part_stats, machine_stats):
    # Extract relevant data
    max_cores, max_mem = machine_stats['num_cores'], machine_stats['memory_capacity']
    time, cpu, mem = get_stats(part_stats['stats'][-1])  # TODO: get data from specific timestamp, not last
    prev_time, prev_cpu, _ = get_stats(part_stats['stats'][-2])

    # Calculate CPU and memory usage
    cpu_usage = 0
    if time != prev_time:
        cpu_usage = (cpu - prev_cpu) / (nanosecs(time) - nanosecs(prev_time))
    cpu_percent = float(cpu_usage) / float(max_cores) * 100
    mem_percent = float(mem) / float(max_mem) * 100
    return {
        "time": time,
        "cpu": cpu_percent,
        "memory": mem_percent
    }


def get_machine_usage():
    try:
        cjson = requests.get("http://localhost:8080/api/v1.3/containers").json()
        mjson = requests.get("http://localhost:8080/api/v1.3/machine").json()
    except:
        return None
    return get_usage(cjson, mjson)


def get_container_usage():
    try:
        cjson = requests.get("http://localhost:8080/api/v1.3/docker/").json()
        mjson = requests.get("http://localhost:8080/api/v1.3/machine").json()
    except:
        return None

    def make_usage_object(entry):
        usage = get_usage(entry, mjson)
        usage["container"] = entry["id"]
        return usage

    return list(map(lambda key: make_usage_object(cjson[key]), cjson.keys()))


if __name__ == "__main__":
    host_performance = get_machine_usage()
    # host_performance["host"] = sys.argv[1] TODO: add host field
    # requests.post("http://mongoapi:8000/performance", data=host_performance)
    print(host_performance)

    container_performance = get_container_usage()
    # requests.post("http://mongoapi:8000/performance", data=container_performance)
    print(container_performance)
