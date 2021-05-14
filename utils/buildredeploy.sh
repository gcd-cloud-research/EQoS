#!/bin/bash

if [ "$#" -lt 1 ]; then
  echo "Usage: $(basename "$0") <deployment name> [<image name>]" || exit 1
fi

deployment="$1"
if [ "$#" -lt 2 ]; then
  image=$deployment
else
  image="$2"
fi

buildimages.sh "$REGISTRY" "$image"
redep.sh "$deployment"
kubectl get pods -o wide
