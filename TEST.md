# Running the Tests

## Prerequisites

Python 3.10+ and a virtual environment with the test dependencies installed.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-test.txt -r app/requirements.txt
playwright install chromium      # download headless browser for e2e tests
```

## Run all tests

```bash
pytest
```

pytest is configured in `pytest.ini` to:

- look for tests under the `tests/` directory
- measure coverage on `app/app.py`
- fail the run if coverage drops below **100%**

## Run by layer

```bash
pytest tests/unit/          # Isolated helpers and routes (mocked DB, 24 tests)
pytest tests/integration/   # DB helpers against real SQLite (7 tests)
pytest tests/api/           # HTTP endpoints via Flask test client (21 tests)
pytest tests/e2e/           # Playwright browser tests (31 tests)
```

## Run with verbose output

```bash
pytest -v
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
├── conftest.py              # shared fixtures: app (session), clean_db (autouse)
├── unit/
│   ├── test_db_helpers.py   # DB helpers — sqlite3/os mocked, no I/O
│   └── test_routes.py       # Route handlers — get_db mocked, SQL verified
├── integration/
│   └── test_db.py           # DB helpers — real SQLite, no HTTP
├── api/
│   └── test_endpoints.py    # HTTP endpoints — Flask test client + real SQLite
└── e2e/
    ├── conftest.py          # TodoPage POM + live_server_url fixture
    └── test_todo_ui.py      # Playwright tests — real browser + real server
```

### Test isolation

All tests share a single SQLite file (`tests/test.db`, git-ignored).
The `clean_db` autouse fixture in `tests/conftest.py` runs `DELETE FROM todos`
before **every** test, so each scenario starts from an empty database.
The E2E live server runs in a background thread and uses the same file.

### Layer definitions

| Layer | File | Uses | What it verifies |
|---|---|---|---|
| **Unit** | `tests/unit/` | mocked sqlite3/os/get_db | exact API calls, SQL strings, parameter binding |
| **Integration** | `tests/integration/test_db.py` | real SQLite, no HTTP | `get_db`, `close_db`, `init_db` |
| **API** | `tests/api/test_endpoints.py` | Flask test client + real SQLite | every HTTP endpoint, status codes, payloads |
| **E2E** | `tests/e2e/test_todo_ui.py` | Playwright + real Flask server | full UI flows, XSS, persistence |

### Test classes

#### Unit (`tests/unit/test_db_helpers.py`)

| Class | What it covers |
|---|---|
| `TestGetDb` | `os.makedirs` call, `sqlite3.connect` args, `row_factory` assignment, connection caching |
| `TestCloseDb` | `db.close()` called, graceful no-op without connection, error argument accepted |
| `TestInitDb` | CREATE TABLE SQL, all column names present, `commit()` called |

#### Unit (`tests/unit/test_routes.py`)

Functions are called directly (no HTTP client); Flask contexts are opened manually.

| Class | What it covers |
|---|---|
| `TestIndex` | `render_template` called with `"index.html"` |
| `TestHealth` | return value is `200` with `{"status": "ok"}` |
| `TestListTodos` | ORDER BY clause in SQL, serialized rows in response |
| `TestCreateTodo` | stripped text in INSERT params, `commit()`, lastrowid used in SELECT |
| `TestToggleTodo` | NOT done in UPDATE SQL, correct id in params, `commit()`, None row → 404 |
| `TestDeleteTodo` | DELETE SQL with correct id, `commit()` |

#### Integration (`tests/integration/test_db.py`)

| Class | What it covers |
|---|---|
| `TestGetDb` | connection creation and per-request cache |
| `TestCloseDb` | both branches: db open / db never opened |
| `TestInitDb` | table creation and idempotence |

#### API (`tests/api/test_endpoints.py`)

| Class | What it covers |
|---|---|
| `TestIndex` | `GET /` |
| `TestHealth` | `GET /healthz` |
| `TestListTodos` | `GET /api/todos` — empty list, results, ordering |
| `TestCreateTodo` | `POST /api/todos` — valid input, whitespace stripping, 400 errors |
| `TestToggleTodo` | `PATCH /api/todos/<id>/toggle` — toggle on/off, 404 |
| `TestDeleteTodo` | `DELETE /api/todos/<id>` — existing and non-existing id |

#### E2E (`tests/e2e/test_todo_ui.py`)

| Class | What it covers |
|---|---|
| `TestPageLoad` | initial render, empty state, stats at zero |
| `TestAddTodo` | Enter key, ADD button, empty/whitespace guard, ordering, stats |
| `TestToggleTodo` | done class, checkmark, line-through, double toggle, stats |
| `TestDeleteTodo` | removal, empty state return, correct item deleted, stats |
| `TestXSS` | HTML escaping, script not executed, special chars |
| `TestPersistence` | todo, done state, and deletion survive page reload |
