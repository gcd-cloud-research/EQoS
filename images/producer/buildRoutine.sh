#!/bin/bash

routine_id=$1
routine_name=$2

cd /received || exit 1
# Get routine template
cp ../routine ./"$routine_id"dir -r

# Add script to template, changing name but keeping extension
extension=$(echo "$routine_name" | awk -F. '{ print $2 }')
mv "$routine_name" "$routine_id"dir/worker."$extension"

# Build Docker image
docker build -t "$REGISTRY"/"$routine_id" "$routine_id"dir

# Push to registry TODO: image not found
echo "Pushing image..." >> log.log
docker push "$REGISTRY"/"$routine_id" >> log.log
echo "Pushed $REGISTRY/$routine_id. Checking..." >> log.log
docker pull "$REGISTRY"/"$routine_id":latest
if [ $? -eq 1 ]; then
  echo "Error pulling image" >> log.log
else
  echo "Image pulled correctly" >> log.log
fi

# Cleanup
rm "$routine_id"dir -r
docker image rm "$REGISTRY"/"$routine_id"

exit 0
