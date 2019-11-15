#!/bin/bash

if [ ! -d "dockerenv/producer/pending" ]; then
  mkdir "dockerenv/producer/pending"
fi

echo "******** Starting container deployment service... ********"
./routineManager.sh &

cd dockerenv
echo "******** Building images... ********"
ls -F | grep / | awk 'BEGIN{FS="/"}{print $1}' | while read line; do
  if [ -f "$line/Dockerfile" ]; then
    echo "******** Found Dockerfile for $line, building... ********"
    docker build "$line" -t "$line"
    echo ""
  fi
done

echo "******** All built, starting... ********"

docker-compose up &

read
kill "$(ps -e | grep docker-compose | awk '{print $1}')"
kill "$(ps -e | grep routineManager | awk '{print $1}')"
