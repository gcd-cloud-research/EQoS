#!/bin/bash
pauseTime=1 # Time between each check for pending routines
prunePeriod=100 # Number of checks between each image prune

BASE_DIR=/home/docker
PENDING_DIR=$BASE_DIR/pending
TEMPLATE_DIR=$BASE_DIR/routinetemplate

count=0
while true; do
  if [ $count -eq $prunePeriod ]; then
    docker image prune -f
    count=0
  fi
  count=$(($count + 1))

  for line in "$(ls $PENDING_DIR)"; do
    if [ -z "$line" ]; then
      continue
    fi

    extension=$(echo "$line" | awk -F. '{ print $2 }')

    # Create new object in db
    imagename=$(python dbutils/initelem.py "$line" "dbutils/config.json")
    echo "$imagename $line"

    # Create and fill directory for building image
    cp -r $TEMPLATE_DIR "$PENDING_DIR/$imagename"
    cp "dbutils/config.json" "$PENDING_DIR/$imagename"
    mv "$PENDING_DIR/$line" "$PENDING_DIR/$imagename/worker.$extension"

    # Build image and remove directory
    docker build "$PENDING_DIR/$imagename" -t "$imagename"
    rm -r "$PENDING_DIR/$imagename"
    
    # Prepare yaml
    sed -e "s/routinename/$line/" -e "s/imagename/$imagename/" -e "s/params/\"$imagename\", \"$extension\"/" $BASE_DIR/routine.yaml > $PENDING_DIR/$imagename.yaml
    
    # Run job
    kubectl apply -f $PENDING_DIR/$imagename.yaml
    
    rm $PENDING_DIR/$imagename.yaml
  done

  sleep $pauseTime
done    
