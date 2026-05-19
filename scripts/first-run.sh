#!/bin/bash
# Run once after editing .env.production and after DNS is pointed to this EC2 IP
set -e

cd /opt/verato

echo "=== Building and starting containers ==="
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

echo "=== Waiting for DB to be ready ==="
sleep 10

echo "=== Running migrations ==="
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py migrate

echo "=== Creating superuser ==="
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py createsuperuser

echo "=== Getting SSL certificate ==="
echo "Make sure api.verato.twocents.ai DNS A record points to this server's IP first!"
read -p "Press Enter when DNS is ready..."

# Start nginx in HTTP-only mode to serve ACME challenge
certbot certonly \
  --webroot \
  -w /opt/verato/certbot/www \
  -d api.verato.twocents.ai \
  --email kanags@gmail.com \
  --agree-tos \
  --no-eff-email

echo "=== Restarting nginx with SSL ==="
docker compose --env-file .env.production -f docker-compose.prod.yml restart nginx

echo ""
echo "=== Done! API is live at https://api.verato.twocents.ai ==="
echo "=== Swagger docs: https://api.verato.twocents.ai/api/v1/schema/swagger-ui/ ==="
