import sys
from datetime import datetime
from calendar import timegm
import requests


URL = 'http://cadvisor:8080/api/v1.3/'


def nanosecs(ts):
    """Convert timestamp to its equivalent in nanoseconds"""
    whole, decimal = ts.split(".")
    decimal = decimal[:-1]  # Remove final Z
    seconds = timegm(
        datetime.strptime(whole, "%Y-%m-%dT%H:%M:%S").timetuple()
    ) + float("0." + decimal)
    return seconds * 10 ** 9


def get_stats(entry):
    return entry['timestamp'], entry['cpu']['usage']['total'], entry['memory']['usage']


def get_usage(part_stats, machine_stats):
    # Extract relevant data
    part_stats = list(map(lambda entry: get_stats(entry), part_stats['stats']))
    usages = []
    for i in range(1, len(part_stats)):
        time, cpu, mem = part_stats[i]
        prev_time, prev_cpu, _ = part_stats[i-1]

        # Calculate CPU and memory usage
        cpu_usage = 0
        if time != prev_time:
            cpu_usage = (cpu - prev_cpu) / (nanosecs(time) - nanosecs(prev_time))
        cpu_percent = float(cpu_usage) / float(machine_stats["cores"]) * 100
        mem_percent = float(mem) / float(machine_stats["memory"]) * 100
        usages.append({
            "time": time,
            "cpu": cpu_percent,
            "memory": mem_percent
        })
    return usages


def get_machine_usage(machine_specs):
    try:
        cjson = requests.get(URL + "containers").json()
    except requests.ConnectionError:
        return None
    usage = get_usage(cjson, machine_specs)
    with open("hostname") as fh:  # TODO: Create Kubernetes yaml with volume at /etc/hostname
        hostname = fh.read().strip()
    return [{
        "host": hostname,
        "usage": usage
    }]


def get_container_usage(machine_specs):
    try:
        cjson = requests.get(URL + "docker").json()
    except requests.ConnectionError:
        return None

    usages = []
    for container_id in cjson.keys():
        usage = get_usage(cjson[container_id], machine_specs)
        usages.append({
            "container": container_id,
            "usage": usage
        })
    return usages


def get_machine_specs():
    try:
        machine_json = requests.get(URL + "machine").json()
    except requests.ConnectionError:
        return None
    return {
        "cores": machine_json['num_cores'],
        "memory": machine_json['memory_capacity']
    }


if __name__ == "__main__":
    specs = get_machine_specs()
    if not specs:
        print("Specs not available")
        sys.exit()

    host_performance = get_machine_usage(specs)
    if host_performance:
        requests.post("http://mongoapi:8000/performance", data=host_performance)

    container_performance = get_container_usage(specs)
    if container_performance:
        requests.post("http://mongoapi:8000/performance", data=container_performance)
