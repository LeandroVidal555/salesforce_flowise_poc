sudo yum update -y
sudo yum install postgresql15 -y
sudo yum install git -y
sudo yum install telnet -y
sudo yum install pip -y
pip install --no-input Flask
sudo yum install docker -y

sudo usermod -a -G docker ec2-user
id ec2-user
newgrp docker

DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.29.6/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

docker version
docker compose version
sudo systemctl enable docker.service
sudo systemctl start docker.service
git clone https://github.com/FlowiseAI/Flowise.git
cd Flowise && cd docker
docker compose up -d