# CLAUDE.md — docker-todo

Mini Flask todo app used as a practical demo for Docker CI/CD lessons.
This file guides Claude Code when working on the project autonomously.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + Flask 3.1 |
| Database | SQLite (`tests/test.db` for tests, `/data/todos.db` in production) |
| Production server | Gunicorn 23 |
| Frontend | Vanilla JS + HTML/CSS (served by Flask) |
| Container | Docker multi-stage build |
| CI/CD | GitHub Actions + GHCR |

---

## Project structure

```
docker-todo/
├── app/
│   ├── app.py              ← Flask app (backend + routing)
│   ├── requirements.txt    ← Production dependencies only
│   └── templates/
│       └── index.html      ← Vanilla JS SPA frontend
├── tests/
│   ├── conftest.py         ← Shared fixtures: app, clean_db (autouse)
│   ├── unit/
│   │   ├── test_db_helpers.py ← DB helpers with mocked sqlite3/os (11 tests)
│   │   └── test_routes.py     ← Route functions called directly, get_db mocked (16 tests)
│   ├── integration/
│   │   └── test_db.py      ← DB helpers: get_db, close_db, init_db (7 tests)
│   ├── api/
│   │   └── test_endpoints.py ← HTTP endpoints via Flask test client (23 tests)
│   └── e2e/
│       ├── conftest.py     ← TodoPage POM + live_server_url fixture
│       └── test_todo_ui.py ← Playwright E2E tests (32 tests)
├── requirements-test.txt   ← Test dependencies (never add to app/requirements.txt)
├── pytest.ini              ← testpaths, cov (--cov-fail-under=100 passed explicitly)
├── .coveragerc             ← Excludes if __name__ == '__main__'
├── Dockerfile
├── docker-compose.yml      ← Local dev (hot reload, port 5001→5000)
├── docker-compose.prod.yml ← Production override (gunicorn)
├── .dockerignore
├── .gitignore
├── TEST.md                 ← How to run tests (keep up to date)
└── .github/
    └── workflows/
        └── ci-cd.yml
```

---

## Essential commands

### Local dev
```bash
# With Docker (hot reload) — app on http://localhost:5001
docker compose up --build

# Without Docker
cd app && DATABASE_PATH=/tmp/todos.db flask run
```

### Tests
```bash
# All tests (unit + integration + api + e2e) with coverage
pytest

# By layer
pytest tests/unit/          # Isolated helpers and routes (mocked DB)
pytest tests/integration/   # DB helpers against real SQLite
pytest tests/api/           # HTTP endpoints via Flask test client
pytest tests/e2e/           # Playwright browser tests

# E2E with visible browser (useful for demos)
pytest tests/e2e/ --headed

# Generate HTML coverage report
pytest --cov-report=html && open htmlcov/index.html
```

### Docker
```bash
# Build
docker build -t docker-todo .

# Run (host port 5001 — macOS uses 5000 for AirPlay)
docker run -p 5001:5000 -v todo-data:/data docker-todo

# Manual healthcheck
curl http://localhost:5001/healthz
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend HTML |
| GET | `/healthz` | Liveness probe |
| GET | `/api/todos` | List all todos (newest first) |
| POST | `/api/todos` | Create todo (`{"text": "..."}`) |
| PATCH | `/api/todos/<id>/toggle` | Toggle done/undone |
| DELETE | `/api/todos/<id>` | Delete todo |

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

SQLite on a Docker volume. Schema:

```sql
CREATE TABLE todos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT    NOT NULL,
    done       BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Ordering: `ORDER BY created_at DESC, id DESC` — `id DESC` is the tiebreaker
for todos inserted within the same second.

`init_db()` is called at module level (not inside `__main__`)
to ensure compatibility with gunicorn, which imports without executing.

---

## Test database

All tests use a dedicated SQLite file at `tests/test.db` (excluded from git).
The `DATABASE_PATH` env var is set to this path in `tests/conftest.py`
**before** the app module is imported.

The `clean_db` autouse fixture (`tests/conftest.py`) runs a `DELETE FROM todos`
before every test — unit and E2E — so each test starts from a known empty state.

The E2E live server (`werkzeug.make_server`) runs in a background thread using
the same app object and the same `tests/test.db`.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/data/todos.db` | SQLite file path |
| `FLASK_DEBUG` | `0` | `1` enables hot reload and debugger |
| `FLASK_APP` | `app.py` | Flask entry point |

---

## Active skills

Skill files live in `.claude/skills/` and guide Claude Code on specific patterns.
Read the relevant skill before working on the corresponding area.

| Area | Skill file |
|------|-----------|
| Docker & CI/CD (project-specific) | `.claude/skills/docker-cicd.md` |
| Playwright E2E best practices | `.claude/skills/playwright-best-practices/` |
| Playwright browser automation CLI | `.claude/skills/playwright-cli` |
| TDD & testing patterns | `.claude/skills/test-driven-development/` |
| Systematic debugging | `.claude/skills/systematic-debugging/` |
| GitHub Actions | `.claude/skills/github-actions-docs` |
| Git workflow (branching, commits, PRs, releases) | `.claude/skills/git-workflow` |
| API design (REST / GraphQL) | `.claude/skills/api-design-principles` |
| Backend architecture (Clean Arch, DDD) | `.claude/skills/architecture-patterns` |
| Python async & concurrency | `.claude/skills/async-python-patterns` |
| Python performance & profiling | `.claude/skills/python-performance-optimization` |
| Security review (OWASP, XSS, injection) | `.claude/skills/security-review` |

---

## Conventions

- **Never** use the Flask dev server in production — always gunicorn
- **Never** commit `.env`, `*.db`, `*.pem`, `.venv/`
- **Never** add test dependencies to `app/requirements.txt` — use `requirements-test.txt`
- Tests **always** use `tests/test.db` — never the production DB
- E2E live server always runs on a free OS-assigned port (`make_server(port=0)`)
- Every new endpoint **must** have unit tests + at least one E2E test
- Coverage must stay at **100%** (`--cov-fail-under=100` in `pytest.ini`)
- Host port is **5001** (not 5000 — macOS AirPlay Receiver occupies 5000)
- All code, comments, and docs must be written in **English**

---

## Documentation rules

**Always keep the following files up to date** when making changes:

| File | Update when |
|------|------------|
| `app/README.md` | project structure, stack, Docker commands, or CI/CD pipeline change |
| `TEST.md` | new test types, new test commands, or test infrastructure changes |
| `CLAUDE.md` (this file) | structure, stack, endpoints, conventions, or skills change |

Do not leave documentation stale. If you add an endpoint, update the API table.
If you add a test layer, update both `TEST.md` and the project structure above.
If you move or rename a skill, update the Active skills table.

---

## Notes for Claude Code

- Before adding dependencies, update `requirements.txt` (or `requirements-test.txt`)
- After changing any endpoint, update the API section of this file **and** `app/README.md`
- If you add columns to the DB, update both `init_db()` AND the Database section above
- E2E tests are slower (~25 s) — only run them if you changed the frontend or routing
- For gunicorn errors, check first: file ownership (`--chown`), `init_db()` outside `__main__`, port already in use
- `done` is stored as INTEGER (0/1) in SQLite — assert `== 0` / `== 1`, not `False` / `True`
