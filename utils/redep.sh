#!/bin/bash

if [ "$#" -ne 1 ]; then
  echo "Usage: $(basename "$0") <deployment name>" && exit 1
fi

kubectl delete -f "$KUBE_FILE_DIR/$1-deployment.yaml"
kubectl create -f "$KUBE_FILE_DIR/$1-deployment.yaml"