# Running the Tests

## Prerequisites

Python 3.10+ and a virtual environment with the test dependencies installed,
plus a reachable MySQL 8 instance.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-test.txt -r app/requirements.txt
playwright install chromium      # download headless browser for e2e tests
```

### Local MySQL

The dev compose ships a `mysql:8` service. The simplest way to run the
suite is to bring it up first, then point pytest at it.

```bash
docker compose up mysql -d        # starts only the mysql container

DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=todos \
DB_USER=todoapp DB_PASSWORD=todopw DB_SSL_CA="" \
pytest --cov-fail-under=100
```

If the host's port 3306 is already taken (e.g. a system mysqld), edit
`docker-compose.override.yml` to publish on a different host port and
pass `DB_PORT=<that-port>` to pytest.

## Run all tests

```bash
DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=todos \
DB_USER=todoapp DB_PASSWORD=todopw DB_SSL_CA="" \
pytest --cov-fail-under=100
```

`pytest.ini` configures coverage on `app/`. The `--cov-fail-under=100`
flag must be passed explicitly to make the build fail when coverage
drops below 100%. Per-layer runs (see below) display coverage but do
not enforce the threshold — a single layer cannot reach 100% on its own.

## Run by layer

```bash
pytest tests/unit/          # Pure helpers (env parsing) — no DB
pytest tests/integration/   # SQLAlchemy round-trips — real MySQL
pytest tests/api/           # HTTP endpoints — Flask test client + real MySQL
pytest tests/e2e/           # Playwright browser tests — real Flask + real MySQL
```

## Run a single test class or test

```bash
# one class
pytest tests/api/test_endpoints.py::TestCreateTodo

# one test
pytest tests/api/test_endpoints.py::TestCreateTodo::test_empty_text_returns_400
```

## E2E options

```bash
# Show the browser window (useful for demos and debugging)
pytest tests/e2e/ --headed

# Slow down interactions to follow along
pytest tests/e2e/ --headed --slowmo=500
```

## Coverage report

A terminal summary is printed automatically after every run.
To also generate an HTML report:

```bash
pytest --cov-report=html
open htmlcov/index.html
```

## Test structure

```
tests/
├── conftest.py                # shared fixtures: app (session), clean_db (autouse)
├── unit/
│   └── test_db_helpers.py     # build_database_uri / build_connect_args (no DB)
├── integration/
│   └── test_db.py             # SQLAlchemy round-trips against real MySQL
├── api/
│   └── test_endpoints.py      # HTTP endpoints — Flask test client + real MySQL
└── e2e/
    ├── conftest.py            # TodoPage POM + live_server_url fixture
    └── test_todo_ui.py        # Playwright tests — real browser + real server
```

### Test isolation

Tests share the database referenced by the `DB_*` env vars. The
`clean_db` autouse fixture in `tests/conftest.py` issues
`DELETE FROM todos` before **every** test, so each scenario starts from
an empty table. The schema is created once at module import via
`app/app.py`'s module-level `db.create_all()`.

The E2E live server runs in a background thread on a free OS-assigned
port and shares the same database.

### Layer definitions

| Layer           | File                           | Uses                            | What it verifies                                    |
| --------------- | ------------------------------ | ------------------------------- | --------------------------------------------------- |
| **Unit**        | `tests/unit/`                  | nothing — pure helpers          | env-var → SQLAlchemy URL / connect_args translation |
| **Integration** | `tests/integration/test_db.py` | real MySQL, no HTTP             | schema, ORM round-trip, server defaults             |
| **API**         | `tests/api/test_endpoints.py`  | Flask test client + real MySQL  | every HTTP endpoint, status codes, payloads         |
| **E2E**         | `tests/e2e/test_todo_ui.py`    | Playwright + real Flask + MySQL | full UI flows, XSS, persistence                     |

### Test classes

#### Unit (`tests/unit/test_db_helpers.py`)

| Class                  | What it covers                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| `TestBuildDatabaseUri` | DB\_\* env vars become a `mysql+pymysql` URL; default port; charset; required vars fail loudly |
| `TestBuildConnectArgs` | DB_SSL_CA empty/whitespace/missing-file → no SSL; existing file → ssl `{ca: ...}` set          |

#### Integration (`tests/integration/test_db.py`)

| Class         | What it covers                                                              |
| ------------- | --------------------------------------------------------------------------- |
| `TestSchema`  | `todos` table exists; `db.create_all()` is idempotent                       |
| `TestSession` | round-trip a `Todo`; `done` defaults to 0; `created_at` populated by server |

#### API (`tests/api/test_endpoints.py`)

| Class            | What it covers                                                    |
| ---------------- | ----------------------------------------------------------------- |
| `TestIndex`      | `GET /`                                                           |
| `TestHealth`     | `GET /healthz`                                                    |
| `TestListTodos`  | `GET /api/todos` — empty list, results, ordering                  |
| `TestCreateTodo` | `POST /api/todos` — valid input, whitespace stripping, 400 errors |
| `TestToggleTodo` | `PATCH /api/todos/<id>/toggle` — toggle on/off, 404               |
| `TestDeleteTodo` | `DELETE /api/todos/<id>` — existing and non-existing id           |

#### E2E (`tests/e2e/test_todo_ui.py`)

| Class             | What it covers                                                 |
| ----------------- | -------------------------------------------------------------- |
| `TestPageLoad`    | initial render, empty state, stats at zero                     |
| `TestAddTodo`     | Enter key, ADD button, empty/whitespace guard, ordering, stats |
| `TestToggleTodo`  | done class, checkmark, line-through, double toggle, stats      |
| `TestDeleteTodo`  | removal, empty state return, correct item deleted, stats       |
| `TestXSS`         | HTML escaping, script not executed, special chars              |
| `TestPersistence` | todo, done state, and deletion survive page reload             |
