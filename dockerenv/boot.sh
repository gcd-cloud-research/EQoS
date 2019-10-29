#!/bin/bash

ls -F | grep / | awk 'BEGIN{FS="/"}{print $1}' | while read line; do
  if [ -f "$line/Dockerfile" ]; then
    echo "************************* Found Dockerfile for $line, building... **************************"
    docker build "$line" -t "$line"
    echo ""
  fi
done

echo "********************************** All built, starting... **********************************"

docker-compose up
