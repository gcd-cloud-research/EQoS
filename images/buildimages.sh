#!/bin/bash

function log() {
  echo "$(date) - $1"
}

if [ "$#" -eq 1 ]; then
	registry=$1
	log "Set registry to $registry"
fi

log "Searching for images to build"
for dir in $(ls -F | grep '\/$'); do
  if [ -f "$dir/Dockerfile" ]; then
    log "Found Dockerfile for $dir, building"
    imagename=$(echo "$dir" | awk 'BEGIN{FS="/"}{print $1}')
    docker build "$dir" -t "$imagename"
    echo ""
    
    if [ ! -z "$registry" ]; then
    	log "Pushing image to registry ($registry/$imagename)"
    	docker tag "$imagename" "$registry/$imagename"
    	docker push "$registry/$imagename"
    fi
  fi
done
if [ ! -z "$registry" ]; then
  log "Images built, cleaning"
	docker image prune -f
fi
log "Done, exiting"
