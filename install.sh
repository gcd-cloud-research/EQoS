
# Update the system
yum update -y

# Tools
yum install -y wget
yum install -y git

# Python
yum install gcc openssl-devel bzip2-devel libffi-devel -y
cd /usr/src
wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tgz
tar xzf Python-3.7.4.tgz
cd Python-3.7.4
./configure --enable-optimizations
make altinstall
rm /usr/src/Python-3.7.4.tgz

# Docker CE
sudo yum install -y yum-utils device-mapper-persistent-data lvm2
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce -y
sudo usermod -aG docker $(whoami)
sudo systemctl enable docker.service
sudo systemctl start docker.service

# Docker machine
curl -L https://github.com/docker/machine/releases/download/v0.8.1/docker-machine-`uname -s`-`uname -m` >/tmp/docker-machine && \
chmod +x /tmp/docker-machine && \
sudo cp /tmp/docker-machine /usr/local/bin/docker-machine

# Docker compose
sudo yum install epel-release -y
pip3.7 install docker-compose
pip3.7 install --upgrade pip
docker-compose version

# Go
wget https://dl.google.com/go/go1.13.linux-amd64.tar.gz
sha256sum go1.13.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.13.linux-amd64.tar.gz
echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.bash_profile
source ~/.bash_profile

# Godep
go get github.com/tools/godep

echo "export PATH=$PATH:$(go env GOPATH)/bin" >> ~/.bash_profile
echo "export GOPATH=$(go env GOPATH)" >> ~/.bash_profile
source ~/.bash_profile

#Open Nebula (Rancher plugin)
go get github.com/OpenNebula/docker-machine-opennebula
cd $GOPATH/src/github.com/OpenNebula/docker-machine-opennebula
make build
make install
echo "export PATH=$PATH:$(which docker-machine-driver-opennebula)" >> ~/.bash_profile
echo "export ONE_AUTH=~/.one/one_auth" >> ~/.bash_profile
echo "export ONE_XMLRPC=http://access.stormy.udl.cat:2633/RPC2" >> ~/.bash_profile
source ~/.bash_profile



# Rancher
docker-machine --debug create --driver opennebula --opennebula-network-id 15 --opennebula-image-id 387 --opennebula-image-owner spos --opennebula-b2d-size 61440 rancher-server


docker run -d --restart=unless-stopped -p 8080:8080 rancher/server

