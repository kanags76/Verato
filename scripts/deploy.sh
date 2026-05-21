#!/bin/bash
# Run on EC2 to deploy latest code from main branch
set -e

cd /opt/verato

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Rebuilding and restarting containers ==="
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

echo "=== Running migrations ==="
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py migrate

echo "=== Reloading nginx ==="
docker compose --env-file .env.production -f docker-compose.prod.yml restart nginx

echo "=== Deploy complete ==="
