#!/bin/bash

echo "***** Searching for images to build *****"
for dir in $(ls -l | awk '/^d/ {print $9}'); do
  if [ -f "$dir/Dockerfile" ]; then
    echo "***** Found Dockerfile for $dir, building *****"
    docker build $dir -t $dir
    echo ""
  fi
done
echo "***** Images built, exiting *****"
