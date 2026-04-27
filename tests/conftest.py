import os
from collections.abc import Generator

import pytest
from flask import Flask

# Set DATABASE_PATH before importing app.app — the module-level init_db() reads it.
TEST_DATABASE = os.path.join(os.path.dirname(__file__), "test.db")
os.environ["DATABASE_PATH"] = TEST_DATABASE

import app.app as app_module  # noqa: E402
from app.app import app as flask_app  # noqa: E402

# ── pytest-flask integration ──────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Session-scoped app fixture required by pytest-flask.
    Provides the `client` and `live_server` fixtures automatically."""
    flask_app.config["TESTING"] = True
    yield flask_app


# ── Database isolation ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    """Truncate all rows before each test so tests never share state.
    The schema (created once at module import) is preserved."""
    with flask_app.app_context():
        db = app_module.get_db()
        db.execute("DELETE FROM todos")
        db.commit()
    yield
