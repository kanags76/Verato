# Verato Backend — AWS Deployment Guide

Target: `https://api.verato.twocents.ai`  
Stack: EC2 t3.small · Docker Compose · nginx · Let's Encrypt SSL  
Region: `us-east-1`

---

## Prerequisites

- AWS account with IAM user that has AdministratorAccess
- AWS CLI v2 installed and configured
- GitHub CLI (`gh`) authenticated
- Domain managed in Route 53

---

## 1. AWS CLI Setup

```bash
brew install awscli
aws configure
# Enter: Access Key ID, Secret Access Key, region (us-east-1), output (json)

# Verify
aws ec2 describe-availability-zones --query 'AvailabilityZones[0].RegionName'
```

---

## 2. Launch EC2 Instance

```bash
# Get latest Ubuntu 22.04 AMI
AMI=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
             "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)

# Create SSH key pair
mkdir -p ~/.ssh
aws ec2 create-key-pair \
  --key-name verato-ec2 \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/verato-ec2.pem
chmod 400 ~/.ssh/verato-ec2.pem

# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name verato-backend-sg \
  --description "Verato backend HTTP HTTPS SSH" \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22  --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80  --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI \
  --instance-type t3.small \
  --key-name verato-ec2 \
  --security-group-ids $SG_ID \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=verato-backend}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance: $INSTANCE_ID"

# Wait for it to start
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
```

---

## 3. Elastic IP (Static IP)

```bash
# Allocate
ALLOC_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' \
  --output text)

# Attach to instance
aws ec2 associate-address \
  --instance-id $INSTANCE_ID \
  --allocation-id $ALLOC_ID

# Get the IP
aws ec2 describe-addresses \
  --allocation-ids $ALLOC_ID \
  --query 'Addresses[0].PublicIp' \
  --output text
```

Current Elastic IP: `98.87.229.254`

---

## 4. Route 53 DNS

```bash
# Get hosted zone ID
aws route53 list-hosted-zones --query 'HostedZones[*].[Name,Id]' --output table

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z03649572M2VN6BBFBEDC \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.verato.twocents.ai",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "98.87.229.254"}]
      }
    }]
  }'

# Verify propagation
dig +short api.verato.twocents.ai
```

---

## 5. Bootstrap the EC2 Server

```bash
# Copy setup scripts to server
scp -i ~/.ssh/verato-ec2.pem \
  scripts/setup-ec2.sh \
  scripts/first-run.sh \
  scripts/deploy.sh \
  ubuntu@api.verato.twocents.ai:~/

# SSH in
ssh -i ~/.ssh/verato-ec2.pem ubuntu@api.verato.twocents.ai

# On the server — install Docker
sudo bash ~/setup-ec2.sh
```

---

## 6. GitHub Deploy Key

The repo is private. Generate an SSH deploy key on the EC2 server:

```bash
# On the EC2 server
ssh-keygen -t ed25519 -C "verato-ec2" -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub
```

Add the public key to the repo (run locally):

```bash
gh repo deploy-key add - --repo kanags76/Verato --title "verato-ec2" <<< "<paste public key here>"
```

Clone the repo on the server:

```bash
# On the EC2 server
echo -e "Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  StrictHostKeyChecking no" >> ~/.ssh/config

git clone git@github.com:kanags76/Verato.git /tmp/verato
sudo mv /tmp/verato /opt/verato
sudo chown -R ubuntu:ubuntu /opt/verato
```

---

## 7. Configure Environment

```bash
# Copy .env.production template
cd /opt/verato
cp .env.production.template .env.production
```

Or `scp` a pre-filled file from your Mac:

```bash
scp -i ~/.ssh/verato-ec2.pem .env.production ubuntu@api.verato.twocents.ai:/opt/verato/.env.production
```

Key variables to fill in:

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DB_PASSWORD` | Strong password, any value — Postgres runs in Docker |
| `GEMINI_API_KEY` | From [aistudio.google.com](https://aistudio.google.com) → Get API key |
| `CORS_ALLOWED_ORIGINS` | Your frontend URL — update when frontend is deployed |
| `SENDGRID_API_KEY` | Optional — needed for weekly digest emails |
| `SLACK_*` | Optional — needed for Slack nudges |

---

## 8. First Deploy

```bash
# On EC2 server — pull latest and start
cd /opt/verato
git pull origin main
sudo bash ~/first-run.sh
```

`first-run.sh` does:
1. `docker compose up --build`
2. `migrate`
3. `createsuperuser`
4. Obtains Let's Encrypt SSL cert for `api.verato.twocents.ai`
5. Restarts nginx with HTTPS

---

## 9. Verify

```bash
# API root
curl https://api.verato.twocents.ai/api/v1/

# Swagger docs
open https://api.verato.twocents.ai/api/v1/schema/swagger-ui/
```

---

## 10. Subsequent Deploys

Push code to `main` on GitHub, then on the EC2 server:

```bash
cd /opt/verato && bash scripts/deploy.sh
```

Or SSH in and run it:

```bash
ssh -i ~/.ssh/verato-ec2.pem ubuntu@api.verato.twocents.ai "cd /opt/verato && bash scripts/deploy.sh"
```

> **Important:** `deploy.sh` always runs `docker compose up -d --build`, which rebuilds the image from the latest code.  
> Never use `docker compose restart web` alone — that reuses the **old image** and your code changes will not be picked up.  
> After any Python code change (views, models, tasks, serializers): **always rebuild**.

The deploy script runs three steps automatically:
1. `git pull origin main` — fetch latest code
2. `docker compose up -d --build` — rebuild image + restart all containers
3. `python manage.py migrate` — apply any pending migrations

---

## AWS Resources Summary

| Resource | ID / Value |
|---|---|
| EC2 Instance | `i-0d5faa6d9de340172` |
| Instance type | `t3.small` (us-east-1) |
| Elastic IP | `98.87.229.254` |
| Security Group | `sg-01473198408b4a457` |
| SSH Key | `~/.ssh/verato-ec2.pem` |
| Route 53 Zone | `Z03649572M2VN6BBFBEDC` (twocents.ai) |
| DNS | `api.verato.twocents.ai` |

---

## Gemini / AI

The backend uses Google Gemini for transcript extraction.  
Auth: `GEMINI_API_KEY` env var (Google AI Studio API key).  
Falls back to Vertex AI ADC for local development.

**Rotate the API key** at [aistudio.google.com](https://aistudio.google.com) if it is ever exposed.

---

## Current Production State (as of May 2026)

### Access

| Item | Value |
|------|-------|
| EC2 IP | `98.87.229.254` |
| SSH user | `ubuntu` |
| SSH key | `~/.ssh/verato-ec2.pem` |
| App path | `/opt/verato` |
| API | `https://api.verato.twocents.ai` |
| Frontend | `https://ais-dev-ecrwhyp7mx4gyc7gxgjoek-18239168023.asia-east1.run.app` |

```bash
ssh -i ~/.ssh/verato-ec2.pem ubuntu@98.87.229.254
```

---

### Docker Services

| Service name | Role |
|-------------|------|
| `web` | Django / Gunicorn |
| `celery` | Async worker (queues: default, extractions, notifications) |
| `celery-beat` | Scheduled task runner |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 |
| `nginx` | Reverse proxy + SSL |

```bash
# Check status
docker compose --env-file .env.production -f docker-compose.prod.yml ps

# View logs
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f web
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f celery
```

---

### Correct Deploy Process

Code is **baked into the Docker image** — not volume-mounted. Always rebuild after any code change:

```bash
# From local — push code
git push origin main

# On EC2
ssh -i ~/.ssh/verato-ec2.pem ubuntu@98.87.229.254
cd /opt/verato
git pull origin main
docker compose --env-file .env.production -f docker-compose.prod.yml build web celery celery-beat
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-deps web celery celery-beat
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py migrate
```

Or from local in one command (after pushing):
```bash
ssh -i ~/.ssh/verato-ec2.pem ubuntu@98.87.229.254 "cd /opt/verato && bash scripts/deploy.sh"
```

**Env-only changes** (no code change) — no rebuild needed, just scp + restart:
```bash
scp -i ~/.ssh/verato-ec2.pem .env.production ubuntu@98.87.229.254:/opt/verato/.env.production
ssh -i ~/.ssh/verato-ec2.pem ubuntu@98.87.229.254 "cd /opt/verato && docker compose --env-file .env.production -f docker-compose.prod.yml restart web celery celery-beat"
```

---

### Celery Beat Schedule

| Task | Schedule |
|------|----------|
| `recompute_risk_scores` | Every 24 hours |
| `send_deadline_nudges` | Daily 09:00 UTC |
| `send_weekly_digest` | Monday 07:00 UTC |
| `poll_gmail_replies` | Every 30 minutes |

---

### Environment Variables

#### Slack
| Variable | Notes |
|----------|-------|
| `SLACK_BOT_TOKEN` | `xoxb-...` — get from Slack app → OAuth & Permissions. **Currently blank — DMs won't fire without this.** |
| `SLACK_SIGNING_SECRET` | Slack app → Basic Information |
| `SLACK_CLIENT_ID` | `8245684161444.11177749142678` |
| `SLACK_CLIENT_SECRET` | Slack app → Basic Information |
| `SLACK_OAUTH_REDIRECT_URI` | `https://api.verato.twocents.ai/api/v1/slack/oauth/callback/` |

#### Gmail OAuth (per-org email sending + reply polling)
| Variable | Notes |
|----------|-------|
| `GOOGLE_CLIENT_ID` | Google Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | Same as above |
| `GOOGLE_GMAIL_REDIRECT_URI` | `https://api.verato.twocents.ai/api/v1/gmail/oauth/callback/` |

Gmail API must be enabled in Google Cloud Console. Each org connects via the OAuth flow — tokens stored in `org.settings` (not env vars).

---

### Key Admin / API URLs

| URL | Purpose |
|-----|---------|
| `/admin/` | Django admin |
| `/api/v1/schema/swagger-ui/` | Swagger docs |
| `/api/v1/gmail/status/` | Gmail connection status (per org) |
| `/api/v1/gmail/oauth/start/?auth=<jwt>` | Start Gmail OAuth flow |
| `/api/v1/slack/status/` | Slack connection status |
| `/api/v1/slack/oauth/start/?auth=<jwt>` | Start Slack OAuth flow |

---

### Useful One-liners

```bash
# Django shell
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py shell

# Run a task immediately
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py shell -c \
  "from apps.notifications.tasks import send_deadline_nudges; send_deadline_nudges.delay()"

# Check all migrations applied
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py showmigrations

# Collect static files
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Renew SSL cert
certbot renew && docker compose --env-file .env.production -f docker-compose.prod.yml restart nginx
```
