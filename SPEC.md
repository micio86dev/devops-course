# System Specification — docker-todo

> **Spec-Driven Development (SDD)**: this file defines the _expected_ behaviour of every
> system layer. Implementation is only correct when it satisfies every assertion below.
> Update this file whenever a spec changes; never let code drift silently.

---

## 1. Application

### 1.1 HTTP API

| Spec ID | Assertion                                                                               |
| ------- | --------------------------------------------------------------------------------------- |
| APP-01  | `GET /healthz` returns HTTP 200 with body `{"status": "ok"}` within 5 s                 |
| APP-02  | `GET /api/todos` returns a JSON array ordered `created_at DESC, id DESC`                |
| APP-03  | `POST /api/todos` with `{"text": "…"}` creates a todo and returns HTTP 201              |
| APP-04  | `POST /api/todos` with missing or empty `text` returns HTTP 400                         |
| APP-05  | `PATCH /api/todos/<id>/toggle` flips `done` (0→1 or 1→0) and returns the updated object |
| APP-06  | `PATCH /api/todos/<id>/toggle` with unknown `id` returns HTTP 404                       |
| APP-07  | `DELETE /api/todos/<id>` removes the todo and returns HTTP 204 (no body)                |
| APP-08  | `GET /` returns HTTP 200 with `text/html` content type (SPA shell)                      |

### 1.2 Database

| Spec ID | Assertion                                                                                                                                     |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| DB-01   | Schema: table `todos(id INTEGER PK AUTOINCREMENT, text TEXT NOT NULL, done BOOLEAN DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)` |
| DB-02   | `DATABASE_PATH` env var controls the file path; default `/data/todos.db`                                                                      |
| DB-03   | `init_db()` is idempotent — calling it twice does not raise or reset data                                                                     |
| DB-04   | `done` is stored as INTEGER (0 or 1), never as Python bool                                                                                    |

### 1.3 Runtime

| Spec ID | Assertion                                                         |
| ------- | ----------------------------------------------------------------- |
| RT-01   | Production server is Gunicorn (never Flask dev server)            |
| RT-02   | App process runs as non-root (`appuser`) inside the container     |
| RT-03   | Container exposes port **5000** internally; host maps to **5001** |
| RT-04   | `FLASK_DEBUG=0` in all production environments                    |

---

## 2. Tests

| Spec ID | Assertion                                                                  |
| ------- | -------------------------------------------------------------------------- |
| TEST-01 | Line coverage ≥ 100 % across `app/` (enforced with `--cov-fail-under=100`) |
| TEST-02 | All tests use `tests/test.db`; production DB is never touched              |
| TEST-03 | Every test starts from an empty `todos` table (autouse `clean_db` fixture) |
| TEST-04 | E2E live server runs on an OS-assigned port (never hardcoded)              |
| TEST-05 | Unit tests mock the DB layer; no SQLite I/O in `tests/unit/`               |

---

## 3. Docker

| Spec ID | Assertion                                                                                                                                                    |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DOCK-01 | Dockerfile uses a multi-stage build: `builder` (deps) → `runtime` (final image)                                                                              |
| DOCK-02 | Final image base is `python:3.12-slim`; no pip, no build tools in runtime stage                                                                              |
| DOCK-03 | HEALTHCHECK polls `GET /healthz` every 30 s (timeout 5 s, 3 retries, 10 s start)                                                                             |
| DOCK-04 | Three-file compose pattern: `docker-compose.yml` (base) + `docker-compose.override.yml` (dev, auto-loaded) + `docker-compose.prod.yml` (prod, explicit `-f`) |
| DOCK-05 | Dev compose (`override.yml`): hot-reload via `./app:/app`, port `5001:5000`, `FLASK_DEBUG=1`                                                                 |
| DOCK-06 | Prod compose: image from GHCR, port `5001:5000`, `FLASK_DEBUG=0`, 4 Gunicorn workers; **no `./app:/app` bind mount**                                         |
| DOCK-07 | Prod compose: only `/mnt/todo-data:/data` volume (NFS); no named volume `todo-data`                                                                          |
| DOCK-08 | Prod compose: resource limits CPU 1, memory 256 M; log rotation 10 M × 3 files                                                                               |
| DOCK-09 | Prod compose: `REDIS_URL` env var set from Valkey URI (app may ignore; infra must wire it)                                                                   |

---

## 4. CI/CD Pipeline (GitHub Actions)

### 4.1 Trigger rules

| Spec ID | Assertion                                                                                  |
| ------- | ------------------------------------------------------------------------------------------ |
| CI-01   | On **push to main/master**: run lint → test → build-push → deploy-production               |
| CI-01b  | On **push of a `stage-*` tag** (any branch): run lint → test → build-push → deploy-staging |
| CI-02   | On **pull request to main/master**: run lint + test only (no push, no deploy)              |

### 4.2 Lint job

| Spec ID | Assertion                                                         |
| ------- | ----------------------------------------------------------------- |
| CI-03   | `ruff format --check app/` exits 0                                |
| CI-04   | `ruff check app/` exits 0                                         |
| CI-05   | `mypy app/` (strict) exits 0                                      |
| CI-06   | `prettier --check` passes on HTML templates, JSON, YAML, Markdown |

### 4.3 Test job

| Spec ID | Assertion                                                                                   |
| ------- | ------------------------------------------------------------------------------------------- |
| CI-07   | Full pytest suite (unit + integration + api + e2e) passes with `DATABASE_PATH=/tmp/test.db` |
| CI-08   | Coverage enforcement: `--cov-fail-under=100` must not fail                                  |

### 4.4 Build & Push job

| Spec ID | Assertion                                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------------------------- |
| CI-09   | Runs only on `push` event (skipped on PR)                                                                               |
| CI-10   | Multi-arch build: `linux/amd64` and `linux/arm64`                                                                       |
| CI-11   | Image pushed to GHCR as `ghcr.io/<owner>/<repo>/docker-todo:<tag>`                                                      |
| CI-12   | Tags: `latest` (default branch), `sha-<short>` (always), `v<semver>` (if semver Git tag), `<tag-name>` (if any Git tag) |
| CI-13   | Build cache stored in GHCR (mode=max) for layer reuse                                                                   |

### 4.5 Deploy jobs

| Spec ID | Assertion                                                                                                                    |
| ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| CI-14   | Compose files (`docker-compose.yml`, `docker-compose.prod.yml`) are SCP'd to **all** app nodes before running docker compose |
| CI-15   | Deploy runs on **all** app nodes in `DEPLOY_HOSTS` (comma-separated IPs)                                                     |
| CI-16   | `REDIS_URL` is sourced from `/root/docker-todo/.env.valkey` before `docker compose up`                                       |
| CI-17   | Post-deploy healthcheck hits `http://localhost:5001/healthz` on each node and exits 1 on failure                             |
| CI-18   | Old dangling images are pruned after successful update                                                                       |
| CI-19   | `deploy-production` runs only when `github.ref` is `refs/heads/main` or `refs/heads/master`; uses environment `production`   |
| CI-20   | `deploy-staging` runs only when `github.ref` starts with `refs/tags/stage-`; uses environment `staging`                      |
| CI-21   | Staging deploy pulls the image tagged with the git tag name (`github.ref_name`), not `:latest`                               |

### 4.6 Required GitHub Secrets

| Secret           | Value                                                                          |
| ---------------- | ------------------------------------------------------------------------------ |
| `DEPLOY_HOSTS`   | Comma-separated public IPs of app nodes — from `terraform output app_node_ips` |
| `DEPLOY_USER`    | SSH user (`root` for DigitalOcean Ubuntu Droplets)                             |
| `DEPLOY_SSH_KEY` | Ed25519 private key (PEM) corresponding to the key registered in Terraform     |

---

## 5. Infrastructure (summary — see `infrastructure/SPEC.md` for detail)

| Spec ID | Assertion                                                                                                        |
| ------- | ---------------------------------------------------------------------------------------------------------------- |
| INF-01  | Load Balancer forwards `:80 HTTP` → app nodes `:5001 HTTP`                                                       |
| INF-02  | LB health check path is `/healthz`; port 5001                                                                    |
| INF-03  | App nodes are reachable on SSH (port 22) from the internet for CI/CD deploy                                      |
| INF-04  | SQLite data lives on NFS (`/mnt/todo-data`) shared from the DB node via VPC                                      |
| INF-05  | Valkey cluster is reachable from app nodes on private hostname, port 25061 (TLS)                                 |
| INF-06  | After `terraform apply`, `/root/docker-todo/` exists on every app node and `.env.valkey` contains the Valkey URI |

---

## 6. Code Quality

| Spec ID | Assertion                                                                  |
| ------- | -------------------------------------------------------------------------- |
| QC-01   | All Python in `app/` passes `mypy --strict` (full type annotations)        |
| QC-02   | Commit messages follow Conventional Commits (`feat:`, `fix:`, `chore:`, …) |
| QC-03   | Test/lint dependencies never added to `app/requirements.txt`               |
| QC-04   | No `.env`, `*.db`, `*.pem`, `.venv/`, `node_modules/` committed            |
