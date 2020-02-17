#!/bin/bash
pauseTime=1 # Time between each check for pending routines
prunePeriod=100 # Number of checks between each image prune

PUBLIC_DIR=/mnt/public
PENDING_DIR=$PUBLIC_DIR/pending
TEMPLATE_DIR=$PUBLIC_DIR/routinetemplate
ROUTINE_DIR=$PUBLIC_DIR/routines

PRIVATE_DIR=/mnt/private
DB_DIR=$PRIVATE_DIR/dbutils

[ ! -d $TEMPLATE_DIR ] && echo "Template directory not found. Exiting" && exit 1
[ ! -d $PENDING_DIR ] && echo "Pending directory not found. Creating" && mkdir -p $PENDING_DIR
[ ! -d $ROUTINE_DIR ] && echo "Routine directory not found. Creating" && mkdir -p $ROUTINE_DIR

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

    echo "Pending job found: $line. Preparing..."

    extension=$(echo "$line" | awk -F. '{ print $2 }')

    # Create new object in db
    imagename=$(python "$DB_DIR/initelem.py" "$line" "$DB_DIR/config.json")
    echo "$imagename $line"

    # Create and fill directory for building image
    cp -r $TEMPLATE_DIR "$ROUTINE_DIR/$imagename"
    cp "$DB_DIR/config.json" "$ROUTINE_DIR/$imagename/config.json"
    mv "$PENDING_DIR/$line" "$ROUTINE_DIR/$imagename/worker.$extension"

    # Build image
    docker build "$ROUTINE_DIR/$imagename" -t "$REGISTRY/$imagename"
    echo "Image $imagename built"

    # Prepare yaml
    sed -e "s/routinename/$line/" -e "s/imagename/$imagename/" -e "s/params/\"$imagename\", \"$extension\"/" "$TEMPLATE_DIR/routine.yaml" > "$ROUTINE_DIR/$imagename.yaml"

    # Schedule job
    kubectl apply -f "$ROUTINE_DIR/$imagename.yaml"
    echo "Job $imagename.yaml scheduled"

    # Cleanup
    rm -rf "$ROUTINE_DIR/$imagename"
    rm -f "$ROUTINE_DIR/$imagename.yaml"
    echo "Cleanup finished"
  done

  sleep $pauseTime
done
