#!/bin/bash

curl http://192.168.101.102:5000/routine \
  -H 'content-type: multipart/form-data' \
  -F program=@/Users/lluismas/Desktop/Projectes/EQoS/test-routines/initDB.py \
  -F requirements=@/Users/lluismas/Desktop/Projectes/EQoS/test-routines/requirements.txt