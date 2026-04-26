import os
import sys
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

# Dedicated test database — completely separate from dev (/data/todos.db) and
# prod databases. Must be set before the app module is imported so the
# module-level init_db() call targets this file.
TEST_DATABASE = os.path.join(os.path.dirname(__file__), "test.db")
os.environ["DATABASE_PATH"] = TEST_DATABASE

import app as app_module  # noqa: E402
from app import app as flask_app  # noqa: E402


# ── pytest-flask integration ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Session-scoped app fixture required by pytest-flask.
    Provides the `client` and `live_server` fixtures automatically."""
    flask_app.config["TESTING"] = True
    yield flask_app


# ── Database isolation ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all rows before each test so tests never share state.
    The schema (created once at module import) is preserved."""
    with flask_app.app_context():
        db = app_module.get_db()
        db.execute("DELETE FROM todos")
        db.commit()
    yield
