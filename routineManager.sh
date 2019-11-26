#!/bin/bash
pauseTime=1 # Time between each check for pending routines
prunePeriod=100 # Number of checks between each image prune

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

    extension=$(echo "$line" | awk -F. '{ print $2 }')

    # Create new object in db
    imagename=$(python dbutils/initelem.py "$line" "dbutils/config.json")
    echo "$imagename $line"

    # Create and fill directory for building image
    cp -r "dockerenv/producer/worker" "dockerenv/producer/pending/$imagename"
    cp "dbutils/config.json" "dockerenv/producer/pending/$imagename"
    mv "dockerenv/producer/pending/$line" "dockerenv/producer/pending/$imagename/worker.$extension"

    # Build image and remove directory
    docker build "dockerenv/producer/pending/$imagename" -t "$imagename"
    rm -r "dockerenv/producer/pending/$imagename"

    # Run container and remove
    docker run --rm --network dockerenv_default -d "$imagename" wrapper.py $imagename $extension
  done

  sleep $pauseTime
done
