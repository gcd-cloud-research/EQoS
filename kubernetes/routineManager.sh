#!/bin/bash
pauseTime=1 # Time between each check for pending routines
prunePeriod=100 # Number of checks between each image prune

BASE_DIR=$(pwd)
PENDING_DIR=$BASE_DIR/pending
TEMPLATE_DIR=$BASE_DIR/routinetemplate
ROUTINE_DIR=$BASE_DIR/routines

[ ! -d $PENDING_DIR ] && mkdir -p $PENDING_DIR
[ ! -d $TEMPLATE_DIR ] && exit 1

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
    cp -r $TEMPLATE_DIR "$ROUTINE_DIR/$imagename"
    cp "dbutils/config.json" "$ROUTINE_DIR/$imagename/config.json"
    mv "$PENDING_DIR/$line" "$ROUTINE_DIR/$imagename/worker.$extension"

    # Build image
    docker build "$ROUTINE_DIR/$imagename" -t "$imagename"

    # Prepare yaml
    sed -e "s/routinename/$line/" -e "s/imagename/$imagename/" -e "s/params/\"$imagename\", \"$extension\"/" "$TEMPLATE_DIR/routine.yaml" > "$ROUTINE_DIR/$imagename.yaml"

    # Schedule job
    kubectl apply -f "$ROUTINE_DIR/$imagename.yaml"

    # Cleanup
    rm -r "$ROUTINE_DIR/$imagename"
    rm "$ROUTINE_DIR/$imagename.yaml"
  done

  sleep $pauseTime
done
