#!/bin/bash

echo "***** Searching for images to build *****"
for dir in $(ls -F | grep '\/$'); do
  if [ -f "$dir/Dockerfile" ]; then
    echo "***** Found Dockerfile for $dir, building *****"
    docker build $dir -t $(echo $dir | awk 'BEGIN{FS="/"}{print $1}')
    echo ""
  fi
done
echo "***** Images built, exiting *****"
