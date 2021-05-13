docker stop elasticsearch
docker rm elasticsearch
docker run -d --name elasticsearch --network=host -dp 9200:9200 -p 9300:9300 -e "discovery.type=single-node" elasticsearch:7.12.1