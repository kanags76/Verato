#!/bin/bash
# Run once on a fresh Ubuntu 22.04 EC2 instance as root/sudo
set -e

echo "=== Installing Docker ==="
apt-get update -y
apt-get install -y docker.io docker-compose-plugin certbot git curl
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

echo "=== Cloning repo ==="
cd /opt
git clone https://github.com/kanags76/Verato.git verato
cd verato

echo "=== Creating .env.production ==="
cp .env.production.template .env.production
echo ""
echo "NEXT STEP: Edit /opt/verato/.env.production with your real secrets, then run:"
echo "  sudo bash /opt/verato/scripts/first-run.sh"
