# Verato — Infrastructure Reference
## Mac (Apple Silicon) · Homebrew-native · No Docker

> **Session startup and daily workflow → see README.md (top of repo)**

---

## ENVIRONMENT STATUS — What's Installed

### Backend

| Component | Version | Status |
|---|---|---|
| PostgreSQL | 18.3 (Homebrew) | Running, auto-starts on login |
| pgvector | 0.8.2 | Installed + enabled in commitment_os |
| Redis | 7.x (Homebrew) | Running, auto-starts on login |
| Python venv | 3.14 | At `backend/.venv` |
| Django | 6.0.4 | Installed |
| Django REST Framework | 3.17.1 | Installed |
| Celery | 5.6.3 | Installed |
| drf-spectacular | 0.29.0 | Installed (Swagger UI) |
| psycopg2-binary | 2.9.12 | Installed |
| python-decouple | 3.8 | Installed |
| django-celery-results | 2.6.0 | Installed |
| django-cors-headers | latest | Installed — `CORS_ALLOW_ALL_ORIGINS = True` in local |

### Frontend

| Component | Version | Status |
|---|---|---|
| Node.js | 24.13.1 | Installed (system) |
| npm | 11.8.0 | Installed |
| Next.js | 16.2.6 | Installed at `frontend/node_modules` |
| React | 19.2.4 | Installed |
| TypeScript | 5.x | Installed |
| TanStack Query | v5 | Installed (server state) |
| Axios | latest | Installed (API client) |
| React Hook Form + Zod | latest | Installed (form validation) |
| Tailwind CSS | v4 | Installed |

**Backend path:** `~/Documents/Programs/Verato/backend`
**Frontend path:** `~/Documents/Programs/Verato/frontend`
**GitHub repo:** https://github.com/kanags76/Verato (private)
**Database:** `commitment_os` on localhost:5432 (no password — Homebrew auth)

---

## Service Management

```bash
# Status
brew services list | grep -E "postgresql|redis"
pg_isready        # localhost:5432 - accepting connections
redis-cli ping    # PONG

# Start
brew services start postgresql@18
brew services start redis

# Stop
brew services stop postgresql@18
brew services stop redis

# Restart
brew services restart postgresql@18
brew services restart redis

# Logs (if something goes wrong)
tail -f /opt/homebrew/var/log/postgresql@18.log
```

---

## Reset Local DB (nuclear option)

Use this if the database gets corrupted or migrations go wrong.

```bash
dropdb commitment_os
createdb commitment_os
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
cd ~/Documents/Programs/Verato/backend
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

---

## How the Environment Was Set Up (history)

### PostgreSQL 18

```bash
brew install postgresql@18
echo 'export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
brew services start postgresql@18
createdb commitment_os
```

### pgvector

```bash
brew install pgvector
psql commitment_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Redis

```bash
brew install redis
brew services start redis
```

### Python venv + backend dependencies

```bash
cd ~/Documents/Programs/Verato/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Node.js + frontend dependencies

Node.js 24 was already installed on the system.

```bash
cd ~/Documents/Programs/Verato/frontend
npm install      # installs all dependencies from package.json
```

### Frontend environment file

Create `frontend/.env.local` (gitignored):

```bash
# Only needed if Django is not on the default port
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

If the file doesn't exist, the frontend defaults to `http://localhost:8000/api/v1` automatically.

### GitHub

```bash
gh repo create kanags76/Verato --private --source . --remote origin --push
```

---

## API Testing

### Frontend app — primary (Phase 2+)

`http://localhost:3000`

- Full UI — login, dashboard, upload, review, people, settings
- Start with `/register` to create an account, or `/login` if you already have one

### Swagger UI — backend API

`http://localhost:8000/api/schema/ui/`

- Every endpoint listed with full docs
- Execute requests directly in the browser
- JWT auth built in — Authorize once, all calls carry the token

```
1. POST /api/v1/auth/token/ → {"email": "admin@example.com", "password": "admin1234"}
2. Copy the "access" value
3. Click Authorize (top right) → enter: Bearer <token>
```

### Django Admin — data inspection

`http://localhost:8000/admin/`

### REST Client in VS Code — saved test scenarios

Create `.http` files in `backend/api-tests/`:

```http
### Get JWT token
POST http://localhost:8000/api/v1/auth/token/
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "admin1234"
}

### List commitments
GET http://localhost:8000/api/v1/commitments/
Authorization: Bearer {{token}}
```

---

## Dockerfile (create at Phase 3, not before)

### Backend

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

EXPOSE 8000
```

### Frontend

```dockerfile
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Phase 3 — AWS Deployment

After frontend is deployed and tested:

1. Backend → AWS ECS (Fargate) behind ALB
2. Frontend → Vercel (connects to ALB endpoint via `NEXT_PUBLIC_API_URL`)
3. Database → RDS PostgreSQL
4. Redis → ElastiCache
5. Static files → S3 + CloudFront
