sudo yum update -y
sudo yum install postgresql15 -y
sudo yum install git -y
sudo yum install telnet -y
sudo yum install pip -y

rpm --import https://debian.neo4j.com/neotechnology.gpg.key
cat << EOF >  /etc/yum.repos.d/neo4j.repo
[neo4j]
name=Neo4j RPM Repository
baseurl=https://yum.neo4j.com/stable/5
enabled=1
gpgcheck=1
EOF

yum install neo4j-5.26.0 -y