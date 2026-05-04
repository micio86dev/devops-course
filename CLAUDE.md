# CLAUDE.md — docker-todo

Mini Flask todo app used as a practical demo for Docker CI/CD lessons.
This file guides Claude Code when working on the project autonomously.

**Spec-Driven Development (SDD)**: behavioural specs live in `SPEC.md` (app + CI/CD) and
`infrastructure/SPEC.md` (Terraform + cloud-init). Always check specs before implementing and
update them whenever requirements change.

---

## Stack

| Layer             | Technology                                                                            |
| ----------------- | ------------------------------------------------------------------------------------- |
| Backend           | Python 3.12 + Flask 3.1 + Flask-SQLAlchemy 3.x + SQLAlchemy 2.0                       |
| Database          | MySQL 8 (Managed on DigitalOcean in prod; `mysql:8` compose service for dev/CI tests) |
| MySQL driver      | PyMySQL 1.1 + cryptography (caching_sha2_password support)                            |
| Production server | Gunicorn 23                                                                           |
| Frontend          | Vanilla JS + HTML/CSS (served by Flask)                                               |
| Container         | Docker multi-stage build                                                              |
| CI/CD             | GitHub Actions + GHCR                                                                 |

---

## Project structure

```
docker-todo/
├── app/
│   ├── app.py              ← Flask app (routes + module-level db.create_all)
│   ├── db.py               ← SQLAlchemy extension + DB_* env-var helpers
│   ├── models.py           ← Todo ORM model (typed Mapped[] columns)
│   ├── __init__.py         ← package marker + __version__
│   ├── requirements.txt    ← Production dependencies only
│   └── templates/
│       └── index.html      ← Vanilla JS SPA frontend
├── scripts/
│   └── sqlite_to_mysql.py  ← One-shot data migration (manual run, see docs/)
├── tests/
│   ├── conftest.py         ← Shared fixtures: app, clean_db (autouse, ORM)
│   ├── unit/
│   │   └── test_db_helpers.py ← Pure helpers: build_database_uri / build_connect_args
│   ├── integration/
│   │   └── test_db.py      ← SQLAlchemy round-trips against real MySQL
│   ├── api/
│   │   └── test_endpoints.py ← HTTP endpoints via Flask test client + real MySQL (23 tests)
│   └── e2e/
│       ├── conftest.py     ← TodoPage POM + live_server_url fixture
│       └── test_todo_ui.py ← Playwright E2E tests (32 tests)
├── requirements-test.txt   ← Test + lint deps (ruff, mypy — never in app/requirements.txt)
├── pyproject.toml          ← Ruff (format + lint) and MyPy strict config
├── package.json            ← Husky, lint-staged, Prettier, commitlint
├── commitlint.config.js    ← Conventional Commits enforcement
├── .husky/
│   ├── pre-commit          ← lint-staged (ruff + prettier) + mypy
│   └── commit-msg          ← commitlint
├── .prettierrc             ← Prettier config (HTML, JS, CSS, YAML, JSON, MD)
├── .prettierignore
├── pytest.ini              ← testpaths, cov (--cov-fail-under=100 passed explicitly)
├── .coveragerc             ← Excludes __main__ and app/__init__.py
├── Dockerfile
├── docker-compose.yml          ← Base condivisa (healthcheck, DB_* envs, restart)
├── docker-compose.override.yml ← Dev override (auto-caricato; bind mount, FLASK_DEBUG=1, mysql:8 service)
├── docker-compose.prod.yml     ← Prod override (GHCR image, mysql-ca.pem mount, gunicorn, risorse)
├── .dockerignore
├── .gitignore
├── SPEC.md                 ← SDD: behavioural specs for app, CI/CD, Docker
├── TEST.md                 ← How to run tests (keep up to date)
├── docs/
│   └── MYSQL_MIGRATION.md  ← SQLite → Managed MySQL migration runbook
├── infrastructure/
│   ├── SPEC.md             ← SDD: infrastructure specs (Terraform, cloud-init, Valkey, MySQL)
│   └── ...                 ← Terraform files (provider, variables, droplets, LB, Valkey, MySQL)
└── .github/
    └── workflows/
        └── ci-cd.yml       ← lint job (parallel) + test job → build-push → deploy (all nodes)
```

---

## Essential commands

### Local dev

```bash
# Con Docker (hot reload) — app su http://localhost:5001
# Carica automaticamente docker-compose.yml + docker-compose.override.yml.
# Avvia anche un mysql:8 con healthcheck; l'app aspetta che sia pronto.
docker compose up --build

# Senza Docker (richiede comunque MySQL 8 raggiungibile)
docker compose up mysql -d
cd app && DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=todos \
  DB_USER=todoapp DB_PASSWORD=todopw DB_SSL_CA="" flask run
```

### Tests

```bash
# Tests need a reachable MySQL 8. Bring up the dev compose service first.
docker compose up mysql -d

# All tests (unit + integration + api + e2e) with coverage
DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=todos \
DB_USER=todoapp DB_PASSWORD=todopw DB_SSL_CA="" \
pytest --cov-fail-under=100

# By layer (env vars must be set the same way for any DB-touching layer)
pytest tests/unit/          # Pure helpers — no DB
pytest tests/integration/   # SQLAlchemy round-trips against real MySQL
pytest tests/api/           # HTTP endpoints via Flask test client + MySQL
pytest tests/e2e/           # Playwright browser tests + MySQL

# E2E with visible browser (useful for demos)
pytest tests/e2e/ --headed

# Generate HTML coverage report
pytest --cov-report=html && open htmlcov/index.html
```

### Docker

```bash
# Build
docker build -t docker-todo .

# Run (host port 5001 — macOS uses 5000 for AirPlay).
# Container needs DB_* envs at runtime; set them to any reachable MySQL 8.
docker run -p 5001:5000 \
  -e DB_HOST=host.docker.internal -e DB_PORT=3306 \
  -e DB_NAME=todos -e DB_USER=todoapp -e DB_PASSWORD=todopw \
  -e DB_SSL_CA="" \
  docker-todo

# Manual healthcheck
curl http://localhost:5001/healthz
```

---

## API endpoints

| Method | Path                     | Description                     |
| ------ | ------------------------ | ------------------------------- |
| GET    | `/`                      | Frontend HTML                   |
| GET    | `/healthz`               | Liveness probe                  |
| GET    | `/api/todos`             | List all todos (newest first)   |
| POST   | `/api/todos`             | Create todo (`{"text": "..."}`) |
| PATCH  | `/api/todos/<id>/toggle` | Toggle done/undone              |
| DELETE | `/api/todos/<id>`        | Delete todo                     |

### API responses

Todo object:

```json
{
  "id": 1,
  "text": "Buy groceries",
  "done": 0,
  "created_at": "2026-04-23 08:00:00"
}
```

Errors:

- `400` — missing body or empty `text`
- `404` — todo not found (toggle only)
- `204` — delete successful (no body)

---

## Database

MySQL 8 (Managed on DigitalOcean in production; `mysql:8` compose
service in dev/CI). Schema (generated by SQLAlchemy from
`app/models.py`):

```sql
CREATE TABLE todos (
    id         BIGINT        NOT NULL AUTO_INCREMENT,
    text       VARCHAR(1024) NOT NULL,
    done       SMALLINT      NOT NULL DEFAULT 0,
    created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

Ordering: `ORDER BY created_at DESC, id DESC` — `id DESC` is the tiebreaker
for todos inserted within the same second (built via the ORM in `list_todos`).

`db.create_all()` is called at module level (not inside `__main__`)
inside an `app.app_context()` so gunicorn import-time triggers schema
creation. Idempotent (`CREATE TABLE IF NOT EXISTS` semantics) so
restarts never reset data.

---

## Test database

Tests run against a real MySQL 8 server: a `mysql:8` service container
in CI, the dev compose `mysql` service locally. `tests/conftest.py`
seeds `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_SSL_CA`
defaults via `os.environ.setdefault(...)` **before** importing
`app.app`, so the module-level `db.create_all()` finds a reachable
server.

The `clean_db` autouse fixture (`tests/conftest.py`) issues
`db.session.execute(delete(Todo))` before every test — unit and E2E —
so each test starts from an empty `todos` table.

The E2E live server (`werkzeug.make_server`) runs in a background
thread using the same app object and the same database.

---

## Environment variables

| Variable      | Default                      | Description                                                       |
| ------------- | ---------------------------- | ----------------------------------------------------------------- |
| `DB_HOST`     | (required at runtime)        | MySQL host (private VPC hostname in prod, `mysql` in dev compose) |
| `DB_PORT`     | `3306`                       | MySQL port                                                        |
| `DB_NAME`     | (required at runtime)        | Database name                                                     |
| `DB_USER`     | (required at runtime)        | Application user                                                  |
| `DB_PASSWORD` | (required at runtime)        | Password                                                          |
| `DB_SSL_CA`   | `/etc/mysql-ca/mysql-ca.pem` | Path to CA cert (PEM). Empty/missing = no TLS (dev/CI)            |
| `FLASK_DEBUG` | `0`                          | `1` enables hot reload and debugger                               |
| `FLASK_APP`   | `app.py`                     | Flask entry point                                                 |
| `REDIS_URL`   | `` (empty)                   | Valkey URI; written by cloud-init, app ignores it                 |

---

## Active skills

Skill files live in `.claude/skills/` and guide Claude Code on specific patterns.
Read the relevant skill before working on the corresponding area.

| Area                                             | Skill file                                       |
| ------------------------------------------------ | ------------------------------------------------ |
| Docker & CI/CD (project-specific)                | `.claude/skills/docker-cicd.md`                  |
| Playwright E2E best practices                    | `.claude/skills/playwright-best-practices/`      |
| Playwright browser automation CLI                | `.claude/skills/playwright-cli`                  |
| TDD & testing patterns                           | `.claude/skills/test-driven-development/`        |
| Systematic debugging                             | `.claude/skills/systematic-debugging/`           |
| GitHub Actions                                   | `.claude/skills/github-actions-docs`             |
| Git workflow (branching, commits, PRs, releases) | `.claude/skills/git-workflow`                    |
| API design (REST / GraphQL)                      | `.claude/skills/api-design-principles`           |
| Backend architecture (Clean Arch, DDD)           | `.claude/skills/architecture-patterns`           |
| Python async & concurrency                       | `.claude/skills/async-python-patterns`           |
| Python performance & profiling                   | `.claude/skills/python-performance-optimization` |
| Security review (OWASP, XSS, injection)          | `.claude/skills/security-review`                 |

---

## Conventions

- **Never** use the Flask dev server in production — always gunicorn
- **Never** commit `.env`, `*.db`, `*.pem`, `.venv/`, `node_modules/`
- **Never** add test/lint dependencies to `app/requirements.txt` — use `requirements-test.txt`
- Tests **always** use `tests/test.db` — never the production DB
- E2E live server always runs on a free OS-assigned port (`make_server(port=0)`)
- Every new endpoint **must** have unit tests + at least one E2E test
- Coverage must stay at **100%** (`--cov-fail-under=100` in `pytest.ini`)
- Host port is **5001** (not 5000 — macOS AirPlay Receiver occupies 5000)
- All code, comments, and docs must be written in **English**
- All Python code in `app/` must pass `mypy --strict` (type annotations required)
- Commit messages must follow **Conventional Commits** (`feat:`, `fix:`, `chore:`, etc.)
- After `git clone` or when adding a new developer: run `npm install` to install git hooks

---

## Documentation rules

**Always keep the following files up to date** when making changes:

| File                      | Update when                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| `app/README.md`           | project structure, stack, Docker commands, or CI/CD pipeline change        |
| `TEST.md`                 | new test types, new test commands, or test infrastructure changes          |
| `SPEC.md`                 | app behaviour, CI/CD jobs, or Docker specs change                          |
| `infrastructure/SPEC.md`  | infrastructure topology, firewall rules, or bootstrap flow change          |
| `docs/MYSQL_MIGRATION.md` | MySQL provisioning, secrets, cutover, rollback, or follow-up cleanup steps |
| `CLAUDE.md` (this file)   | structure, stack, endpoints, conventions, or skills change                 |

Do not leave documentation stale. If you add an endpoint, update the API table.
If you add a test layer, update both `TEST.md` and the project structure above.
If you move or rename a skill, update the Active skills table.

---

## Notes for Claude Code

- Before adding dependencies, update `requirements.txt` (or `requirements-test.txt`)
- After changing any endpoint, update the API section of this file **and** `app/README.md`
- If you add columns to the DB, update both `app/models.py` AND the Database section above
- E2E tests are slower (~25 s) — only run them if you changed the frontend or routing
- For gunicorn errors, check first: file ownership (`--chown`), `db.create_all()` outside `__main__`, MySQL reachable, port already in use
- `done` is stored as SMALLINT (0/1) in MySQL — assert `== 0` / `== 1`, not `False` / `True` (preserved from the SQLite-era contract)
- New Python functions in `app/` **must** have full type annotations (mypy strict enforces this)
- `app/__init__.py` is excluded from coverage — it only holds `__version__` metadata
- CI/CD deploy secret is `DEPLOY_HOSTS` (comma-separated app node IPs from `terraform output app_node_ips`), NOT a single `DEPLOY_HOST`
- Valkey URI lives on each app node at `/root/docker-todo/.env.valkey` (written by cloud-init, mode 600)
- MySQL connection lives on each app node at `/root/docker-todo/.env.mysql` (mode 600); CA cert at `/root/docker-todo/mysql-ca.pem` (mode 644, bind-mounted into the container at `/etc/mysql-ca/mysql-ca.pem`)
- See `docs/MYSQL_MIGRATION.md` for cutover/rollback runbooks and the GitHub secrets checklist
