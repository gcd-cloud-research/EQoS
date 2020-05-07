#!/bin/bash

if [ "$#" -lt 2 ] || [[ "$1" != "logs" && "$1" != "exec" ]]; then
  echo -e "\tUsage: $(basename "$0") {logs|exec} {name} [logs/exec args]"
  echo -e "\tRuns kubectl logs or kubectl exec with an incomplete pod name"
  exit 1
fi

pods=$(kubectl get pods | grep "$2")
podcount=$(echo "$pods" | wc -l)
if [ "$podcount" -gt 1 ]; then
  if [ "$(echo "$pods" | grep -c Running)" -eq 1 ]; then
    pods=$(echo "$pods" | grep Running)
  else
    echo "Ambiguity in selecting pod. Found:"
    for pod in $(echo "$pods" | awk '{print $1}'); do echo "$pod"; done
    exit 0
  fi
elif [ "$podcount" -lt 1 ]; then
  echo "No pod found"
  exit 0
fi

echo "kubectl $1 $(echo "$pods" | awk '{print $1}')" "${@:3}"
kubectl "$1" "$(echo "$pods" | awk '{print $1}')" "${@:3}"
