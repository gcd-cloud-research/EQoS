#!/bin/bash

if [ "$#" -lt 2 ] || [[ "$1" != "logs" && "$1" != "exec" ]]; then
  echo -e "\tUsage: $(basename "$0") {logs|exec} {name} [logs/exec args]"
  echo -e "\tRuns kubectl logs or kubectl exec with an incomplete pod name"
  exit 1
fi

pods=$(kubectl get pods | grep "$2" | grep Running | awk '{print $1}')
podcount=$(echo "$pods" | wc -l)
if [ "$podcount" -gt 1 ]; then
  echo "Ambiguity in selecting pod. Found:"
  for pod in $pods; do echo "$pod"; done
  exit 0
elif [ "$podcount" -lt 1 ]; then
  echo "No pod found"
  exit 0
fi

echo "kubectl $1 $pods" "${@:3}"
kubectl "$1" "$pods" "${@:3}"
