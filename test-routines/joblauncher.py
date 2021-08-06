import requests
import time
import json

TASK_PATH = "/Users/user/Desktop/DataSciencePython/"
JOB_COUNT = 10

tasks = {
}

with open(TASK_PATH+"logistic_regression_updated.py") as pythonApp, open(TASK_PATH+"requirements.txt") as requirements:
    file_dict = {"program": pythonApp, "requirements": requirements}

    for _ in range(0, JOB_COUNT):
        response = requests.post("http://192.168.101.66:5000/routine", files=file_dict).json()
        print("Task id:", response)
        tasks[response["id"]] = ""

print("Tasks: ", tasks)
performance = {}

while len(tasks.keys()) > 0:
    response = requests.get("http://192.168.101.66:5000/mongo/taskstatus", params={"id": tasks.keys()}).json()
    print(response)
    for task in response:
        print("Checking task %s" % task["id"])
        if task["status"] == "FAILURE":
            print("Task %s failed" % task["id"])
            del tasks[task["id"]]
        elif task["status"] == "SUCCESS":
            print("Task %s finished successfully" % task["id"])
            del tasks[task["id"]]

            performanceResp = requests.get("http://192.168.101.66:5000/mongo/taskperformance", params={"id": task["id"]}).json()
            print(performanceResp)
            performance[task["id"]] = performanceResp

    time.sleep(1)

with open("output.json", "w") as outputFile:
    json.dump(performance, outputFile)
