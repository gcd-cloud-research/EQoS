docker stop kibana
docker rm kibana
docker run -d --name kibana --net elastic -dp 5601:5601 kibana:7.12.1
