import os
from collections.abc import Generator

import pytest
from flask import Flask

# Provide DB_* env vars *before* importing app.app — its module-level
# build_database_uri() and db.create_all() read them at import time.
# Use setdefault so a real environment (CI, dev shell) overrides these
# placeholders. DB_SSL_CA="" disables TLS, which is correct for the local
# mysql:8 service container and the CI service container.
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "todos")
os.environ.setdefault("DB_USER", "todoapp")
os.environ.setdefault("DB_PASSWORD", "todopw")
os.environ.setdefault("DB_SSL_CA", "")
# Disable OTLP tracing in tests: `tempo` hostname is only available inside
# the Docker monitoring network and would cause gRPC connection errors.
os.environ.setdefault("OTLP_ENDPOINT", "")

from sqlalchemy import delete  # noqa: E402

from app.app import app as flask_app  # noqa: E402
from app.db import db  # noqa: E402
from app.models import Todo  # noqa: E402

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
        db.session.execute(delete(Todo))
        db.session.commit()
    yield
