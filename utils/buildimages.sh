#!/bin/bash

function log() {
  echo "$(date) - $1"
}

if [ "$#" -ge 1 ]; then
	registry=$1
	log "Set registry to $registry"
fi

cd "$IMAGE_DIR" || exit 1

log "Searching for images to build"
if [ "$#" -eq 2 ]; then
  search=$2
else
  search=$(ls -F | grep '\/$')
fi

succ=0
fail=0
for dir in $search; do
  if [ -f "$dir/Dockerfile" ]; then
    log "Found Dockerfile for $dir, building"
    imagename=$(echo "$dir" | awk 'BEGIN{FS="/"}{print $1}')
    docker build "$dir" -t "$imagename"
    echo ""

    if [ "$?" -ne 0 ]; then
      fail=$((fail + 1))
      continue
    fi

    if [ ! -z "$registry" ]; then
    	log "Pushing image to registry ($registry/$imagename)"
    	docker tag "$imagename" "$registry/$imagename"
    	docker push "$registry/$imagename"
    fi

    if [ "$?" -ne 0 ]; then
      fail=$((fail + 1))
    else
      succ=$((succ + 1))
    fi
  fi
done
if [ ! -z "$registry" ]; then
  log "Images built, cleaning"
	docker image prune -f
fi
log "Processed $((succ + fail)) images. $succ successes, $fail failures."
log "Exiting"
