#!/bin/bash
# Run once on a fresh Ubuntu 22.04 EC2 instance as root/sudo
set -e

echo "=== Installing Docker (official repo) ==="
apt-get update -y
apt-get install -y ca-certificates curl gnupg git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin certbot

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

echo "=== Docker installed ==="
docker --version
docker compose version

echo ""
echo "NEXT: clone the repo and edit .env.production, then run first-run.sh"
echo "Clone with: git clone https://<TOKEN>@github.com/kanags76/Verato.git /opt/verato"
