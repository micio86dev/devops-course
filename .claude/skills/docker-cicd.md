---
name: docker-cicd
description: Use when modifying the Dockerfile, docker-compose files, or the GitHub Actions CI/CD pipeline in this project. Covers multi-stage build rules, layer order, service configuration, workflow job structure, secrets, image tags, and healthcheck constraints.
---

# Docker & CI/CD

Patterns and rules for modifying the Docker configuration and GitHub Actions workflow
in this project. Read this before touching Dockerfile, docker-compose, or ci-cd.yml.

---

## Dockerfile — multi-stage rules

This project uses **two stages**: `builder` and `runtime`.

```
builder  → installs pip + dependencies into a venv
runtime  → copies venv + code, runs as appuser
```

### Layer order (do not change without a good reason)

```dockerfile
# 1. requirements before code → cacheable layer
COPY app/requirements.txt .
RUN pip install ...

# 2. code after → only invalidated when app/* changes
COPY --chown=appuser:appgroup app/ .
```

Rule: **what changes least goes first**.

### Adding a Python dependency

1. Update `app/requirements.txt`
2. `docker build -t docker-todo .` — the pip layer will be rebuilt
3. Verify: `docker run --rm docker-todo pip list`

### Adding a system package (apt)

Add it in the `builder` stage, **not** `runtime`, unless it's needed at runtime.
Always group into a single `RUN` statement:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

The `rm -rf /var/lib/apt/lists/*` is mandatory — it keeps the image small.

---

## docker-compose — dev vs prod

| File | Use | Key differences |
|------|-----|-----------------|
| `docker-compose.yml` | local dev | bind mount `/app`, FLASK_DEBUG=1, `flask run` |
| `docker-compose.prod.yml` | production | image from GHCR, gunicorn, resource limits |

### External port mapping

The host port is **5001** (not 5000 — macOS AirPlay Receiver occupies 5000).
The container always listens on port 5000 internally.

### Adding a service (e.g. Redis)

Add to `docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

In prod, add the override in `docker-compose.prod.yml` with
`restart: always` and without a public port binding if not necessary.

---

## GitHub Actions — ci-cd.yml

### Job structure

```
test → build-push (push to main only) → deploy (push to main only)
```

Rule: **never modify this chain** without updating the `needs:` dependencies of each job.

### Adding a step to the `test` job

Insert **before** the smoke test, in logical order:

```yaml
- name: Run unit & integration tests
  run: pytest

- name: Run E2E tests
  run: |
    pip install pytest-playwright
    playwright install chromium --with-deps
    pytest tests/e2e/
```

### Adding a secret

1. `Settings → Secrets and variables → Actions → New repository secret`
2. Reference in the workflow: `${{ secrets.SECRET_NAME }}`
3. Never log the value of a secret (`echo $SECRET` is forbidden in workflows)

### Python dependency caching in CI

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
    cache-dependency-path: app/requirements.txt
```

This speeds up every run by avoiding re-downloading packages from scratch.

### Image tags

The workflow automatically generates:
- `:latest` — on every push to main
- `:sha-XXXXXXX` — short commit hash
- `:v1.2.3` — if a Git tag `v1.2.3` exists

To force a deploy of a specific version:
```bash
IMAGE_TAG=sha-abc1234 docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Healthcheck

The `/healthz` endpoint is the verification point for:
- `HEALTHCHECK` in the Dockerfile (Docker daemon)
- `healthcheck:` in docker-compose
- The "Verify deployment" step in the CI workflow

**Do not remove or rename `/healthz` without updating all three.**

If you add external dependencies (Postgres, Redis), extend the healthcheck:

```python
@app.route("/healthz")
def health():
    try:
        get_db().execute("SELECT 1")
        return jsonify({"status": "ok", "db": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 503
```

---

## Useful debug commands

```bash
# Inspect layers and sizes
docker history docker-todo
docker image inspect docker-todo

# Enter the container as appuser
docker exec -it docker-todo-dev sh

# Enter as root (debug only — never in production)
docker exec -it --user root docker-todo-dev sh

# Check healthcheck status
docker inspect --format='{{.State.Health.Status}}' docker-todo-dev

# Run CI workflow locally (act)
brew install act
act push
```
