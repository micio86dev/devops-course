# Docker Todo — CI/CD Guide

A minimal todo app in Flask used as a hands-on example to explain
Docker, multi-stage builds, and CI/CD with GitHub Actions.

---

## Project structure

```
docker-todo/
├── app/
│   ├── app.py              ← Flask backend + serves the frontend
│   ├── requirements.txt
│   └── templates/
│       └── index.html      ← Vanilla JS frontend
│
├── Dockerfile              ← Multi-stage build (builder + runtime)
├── docker-compose.yml      ← Local development environment
├── docker-compose.prod.yml ← Production overrides
├── .dockerignore
└── .github/
    └── workflows/
        └── ci-cd.yml       ← GitHub Actions pipeline
```

---

## Running locally (without Docker)

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_PATH=/tmp/todos.db flask run
# → http://localhost:5000
```

---

## Running with Docker

### Manual build

```bash
# Build
docker build -t docker-todo .

# Run
docker run -p 5001:5000 -v todo-data:/data docker-todo

# → http://localhost:5000
```

### With docker compose (dev, hot reload)

```bash
docker compose up --build
# → http://localhost:5000
# Edit app/app.py → Flask reloads automatically
```

---

## Docker concepts demonstrated

### 1. Multi-stage build

The `Dockerfile` has **two stages**:

| Stage | Purpose |
|-------|---------|
| `builder` | installs pip + dependencies into a venv |
| `runtime` | copies only the compiled venv + application code |

Result: the final image **does not contain pip**, build tools, or cache.

```bash
# Check image size
docker images docker-todo
```

### 2. Layer caching

```dockerfile
COPY requirements.txt .              # ← layer 1: changes rarely
RUN pip install -r requirements.txt  # ← layer 2: cacheable

COPY app/ .                          # ← layer 3: changes often
```

Rule: **put what changes least first** → faster rebuilds.

```bash
# First build (no cache)
time docker build -t docker-todo .

# Edit only app.py, then rebuild → much faster
touch app/app.py
time docker build -t docker-todo .
```

### 3. Do not run as root

```dockerfile
RUN useradd --system appuser
USER appuser
```

```bash
# Verify
docker run --rm docker-todo whoami
# → appuser
```

### 4. Healthcheck

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' docker-todo-dev

# Possible values: starting | healthy | unhealthy
```

### 5. Volume for persistence

```bash
# Data survives container restarts
docker compose down
docker compose up -d
# → todos are still there
```

---

## CI/CD Pipeline — GitHub Actions

```
push to main
    │
    ▼
┌─────────┐     ┌──────────────┐     ┌────────┐
│  test   │────▶│ build & push │────▶│ deploy │
│         │     │   to GHCR    │     │  SSH   │
└─────────┘     └──────────────┘     └────────┘

push on PR
    │
    ▼
┌─────────┐
│  test   │  (lint + smoke test only, no push)
└─────────┘
```

### Secrets to configure in the GitHub repository

```
Settings → Secrets and variables → Actions → New repository secret
```

| Secret | Value |
|--------|-------|
| `DEPLOY_HOST` | server IP or hostname |
| `DEPLOY_USER` | e.g. `ubuntu` |
| `DEPLOY_SSH_KEY` | private SSH key (PEM) |

### Adding the SSH key to the server

```bash
# On your machine: generate a dedicated deploy key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key

# On the server: add the public key
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys

# In GitHub: add the content of deploy_key as the DEPLOY_SSH_KEY secret
cat ~/.ssh/deploy_key
```

### Production server setup

```bash
# On the server
git clone https://github.com/YOUR_USER/docker-todo.git ~/docker-todo

# Log in to GHCR (required to pull private images)
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

---

## Useful commands for the lesson

```bash
# Inspect image layers
docker history docker-todo

# Enter a running container
docker exec -it docker-todo-dev sh

# Stream logs in real time
docker compose logs -f

# Check resource usage
docker stats

# List volumes
docker volume ls
docker volume inspect docker-todo_todo-data

# Clean up everything (warning: also deletes volumes!)
docker compose down -v
```
