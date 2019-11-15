#!/bin/bash
pauseTime=1
prunePeriod=10
count=0
while true; do
  if [ $count -eq $prunePeriod ]; then
    docker image prune -f
    count=0
  fi
  count=$(($count + 1))
  for line in "$(ls "dockerenv/producer/pending")"; do
    if [ -z "$line" ]; then
      continue
    fi
    imagename=$(echo "$line" | awk -F. '{print $1}')
    ls dockerenv/producer/pending
    mkdir "dockerenv/producer/pending/$imagename" & mv "dockerenv/producer/pending/$imagename.py" "dockerenv/producer/pending/$imagename/worker.py"
    docker build "dockerenv/producer/pending/$imagename" -f "dockerenv/producer/workerDockerfile" -t "$imagename"
    docker run -d --rm "$imagename"
    rm -r "dockerenv/producer/pending/$imagename"
  done
  sleep $pauseTime
done
