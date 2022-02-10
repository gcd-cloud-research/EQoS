import json
from datetime import datetime
from os import listdir
from os.path import isfile, join


def getDataFromFile(fileName):
    with open(f"results/{fileName}", "r") as outputFile:
        parsed = json.load(outputFile)
        allKeys = list(parsed.keys())

        taskCount = len(allKeys)
        totalResponse = 0
        totalRun = 0

        minTime = None
        maxTime = None

        for taskKey in allKeys:
            task = parsed[taskKey]
            totalResponse += task["response_time"]
            totalRun += task["run_time"]
            for performance in task["performance"]:
                parsedTime = ''.join(performance["usage"]["time"].split('.')[:-1])
                timestamp = datetime.strptime(parsedTime, '%Y-%m-%dT%H:%M:%S')
                # timestamp = datetime.strptime(performance["usage"]["time"], '%b %d %Y %I:%M%p')
                if not minTime or timestamp < minTime:
                    minTime = timestamp
                if not maxTime or timestamp > maxTime:
                    maxTime = timestamp

        delta = maxTime - minTime
#        print(f"{fileName} - mintime: {minTime} maxtime: {maxTime} delta: {delta.total_seconds()}")
        # print(f"{fileName.split('.')[0]} & {totalRun/taskCount:.2f} & {totalResponse/taskCount:.2f} & {delta.total_seconds()/taskCount}")
        results.append(f"{fileName.split('.')[0]} & {totalRun/taskCount:.2f} & {totalResponse/taskCount:.2f} & {delta.total_seconds()/taskCount} \\ \hline")

        # print(json.dumps(parsed[allKeys[0]], indent=4, sort_keys=True))


onlyfiles = [f for f in listdir('results') if isfile(join('results', f)) if f.endswith(".json")]

results = []
for file in onlyfiles:
    getDataFromFile(file)

results.sort()
for result in results:
    print(result)