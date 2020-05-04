#!/bin/bash

if [ "$#" -ne 1 ]; then
  echo "Usage: $(basename "$0") <image name>" || exit 1
fi

buildimages.sh 192.168.101.76:5000 "$1"
redep.sh "$1"
