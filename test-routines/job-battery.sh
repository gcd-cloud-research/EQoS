#!/bin/bash
for i in $(seq 1 10); do
    curl http://192.168.101.70:5000/routine \
      -H 'content-type: multipart/form-data' \
      -F program=@/home/machine/Desktop/DataSciencePython/logistic_regression_updated.py \
      -F requirements=@/home/machine/Desktop/DataSciencePython/requirements.txt
    sleep 1
done
