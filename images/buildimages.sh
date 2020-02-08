#!/bin/bash

if [ "$#" -eq 1 ]; then
	registry=$1
	echo "Set registry to $registry"
fi

echo "***** Searching for images to build *****"
for dir in $(ls -F | grep '\/$'); do
  if [ -f "$dir/Dockerfile" ]; then
    echo "***** Found Dockerfile for $dir, building *****"
    imagename=$(echo $dir | awk 'BEGIN{FS="/"}{print $1}')
    docker build $dir -t $imagename
    echo ""
    
    if [ ! -z "$registry" ]; then
    	echo "***** Pushing image to registry ($registry/$imagename) *****"
    	docker tag $imagename "$registry/$imagename"
    	docker push "$registry/$imagename"
    fi
  fi
done
echo "***** Images built, cleaning *****"
if [ ! -z "$registry" ]; then
	docker image prune -f
fi
echo "***** Done, exiting *****"
