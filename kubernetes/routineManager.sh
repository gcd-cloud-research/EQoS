#!/bin/bash
pauseTime=1 # Time between each check for pending routines
prunePeriod=100 # Number of checks between each image prune

PUBLIC_DIR=/mnt/public
PENDING_DIR=$PUBLIC_DIR/pending
TEMPLATE_DIR=$PUBLIC_DIR/routinetemplate
ROUTINE_DIR=$PUBLIC_DIR/routines

PRIVATE_DIR=/mnt/private
DB_DIR=$PRIVATE_DIR/dbutils
KUBE_DATA_DIR=$PRIVATE_DIR/kubedata

[ ! -d $TEMPLATE_DIR ] && echo "Template directory not found. Exiting" && exit 1
[ ! -d $PENDING_DIR ] && echo "Pending directory not found. Creating" && mkdir -p $PENDING_DIR
[ ! -d $ROUTINE_DIR ] && echo "Routine directory not found. Creating" && mkdir -p $ROUTINE_DIR
[ ! -d $KUBE_DATA_DIR/tmp ] && echo "Kube data directory not found. Creating" && mkdir -p $KUBE_DATA_DIR/tmp

count=0
while true; do
  if [ $count -eq $prunePeriod ]; then
    docker image prune -f
    count=0
  fi
  count=$((count + 1))

  for line in $(ls $PENDING_DIR); do
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

  deployments=$(kubectl get deployments | awk '{if ($1 != "NAME") print $1}')
  for dep in $deployments; do
    pods=$(kubectl get pods | grep "$dep" | awk '{if ($2 !~ "^0/" && $1 != "NAME") print $1}')
    i=0
    for pod in $pods; do
      ip=$(kubectl describe pod "$pod" | grep "Node:" | awk 'BEGIN{FS="/"}{print $2}')
      port=$(kubectl get service "$dep" | awk '{if ($5 != "PORT(S)") print $5}' | awk 'BEGIN{FS=":"}{print $2}')
      if [ ! -z "$port" ]; then
        echo "$ip $port" > "$KUBE_DATA_DIR/tmp/$dep""_$i"
      fi
      i=$((i+1))
    done
  done

  rm -f $KUBE_DATA_DIR/*
  mv $KUBE_DATA_DIR/tmp/* $KUBE_DATA_DIR/

  sleep $pauseTime
done
