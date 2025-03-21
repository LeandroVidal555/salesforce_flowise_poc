echo "1) INSTALLING DEPENDENCIES"
sudo yum update -y
sudo yum install postgresql15 -y
sudo yum install git -y
sudo yum install telnet -y
sudo yum install pip -y
sudo yum install docker -y

echo "2) CONFIGURING DOCKER USER & USER GROUP"
sudo usermod -a -G docker ec2-user
id ec2-user
newgrp docker

echo "3) INSTALLING DOCKER COMPOSE"
DOCKER_CONFIG=/home/ec2-user/.docker
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.30.3/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
chown -R ec2-user:ec2-user /home/ec2-user/.docker

echo "4) ENABLE+START DOCKER SERVICE"
sudo -u ec2-user sudo systemctl enable docker.service
sudo -u ec2-user sudo systemctl start docker.service

echo "5) CHECK DOCKER VERSIONS"
sudo -u ec2-user docker version
sudo -u ec2-user docker compose version

cd /home/ec2-user

echo "6) CREATING N8N CONFIG FILES"
cat << EOF > .env
POSTGRES_DB=n8n
POSTGRES_PORT=5432
POSTGRES_HOST=$(aws rds describe-db-instances --db-instance-identifier sf-fw-poc-pgres --query "DBInstances[0].Endpoint.Address" --output text)
POSTGRES_NON_ROOT_USER=n8n
POSTGRES_NON_ROOT_PASSWORD=$(aws secretsmanager get-secret-value --secret-id sf-fw-poc-n8n-pgres-creds --query SecretString --output text | jq -r '.password')
EOF

cat << EOF > docker-compose.yml
version: '3.8'

volumes:
  n8n_storage:

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    restart: always
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=\${POSTGRES_HOST}
      - DB_POSTGRESDB_PORT=\${POSTGRES_PORT}
      - DB_POSTGRESDB_DATABASE=\${POSTGRES_DB}
      - DB_POSTGRESDB_USER=\${POSTGRES_NON_ROOT_USER}
      - DB_POSTGRESDB_PASSWORD=\${POSTGRES_NON_ROOT_PASSWORD}
      - DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED=false
      - DB_POSTGRESDB_SSL=true
      - N8N_RUNNERS_ENABLED=true
      - N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true
    ports:
      - 5678:5678
    volumes:
      - n8n_storage:/home/node/.n8n
EOF

chown ec2-user:ec2-user .env docker-compose.yml

echo "7) STARTING N8N"
sudo -u ec2-user docker compose up -d