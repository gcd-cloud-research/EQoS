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

    # Create new object in db
    imagename=$(python initelem.py)
    echo $imagename

    # Create and fill directory for building image
    cp -r "dockerenv/producer/worker" "dockerenv/producer/pending/$imagename"
    echo $imagename > "dockerenv/producer/pending/$imagename/id.txt"
    mv "dockerenv/producer/pending/$line" "dockerenv/producer/pending/$imagename/worker.py"

    # Build image and remove directory
    docker build "dockerenv/producer/pending/$imagename" -t "$imagename"
    rm -r "dockerenv/producer/pending/$imagename"

    # Run container and remove
    docker run --rm --network dockerenv_default -d "$imagename"
  done

  sleep $pauseTime
done
