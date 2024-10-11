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

DOCKER_CONFIG=/home/ec2-user/.docker
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.29.6/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
chown -R ec2-user:ec2-user /home/ec2-user/.docker

sudo -u ec2-user sudo systemctl enable docker.service
sudo -u ec2-user sudo systemctl start docker.service
sudo -u ec2-user docker version
sudo -u ec2-user docker compose version

cd /home/ec2-user
git clone https://github.com/FlowiseAI/Flowise.git
chown -R ec2-user:ec2-user Flowise
cd Flowise && cd docker
# Create the .env file with the desired content
cat <<EOF > .env
PORT=3000
DATABASE_PATH=/root/.flowise
APIKEY_PATH=/root/.flowise
SECRETKEY_PATH=/root/.flowise
LOG_PATH=/root/.flowise/logs
BLOB_STORAGE_PATH=/root/.flowise/storage
EOF

sudo -u ec2-user docker compose up -d