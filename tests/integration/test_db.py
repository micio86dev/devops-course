"""Integration tests — DB helpers.

These tests exercise get_db / close_db / init_db against a real SQLite file.
No HTTP layer is involved: each test opens its own app_context directly.
Test isolation is provided by the clean_db autouse fixture in tests/conftest.py.
"""

import sqlite3

import app.app as app_module
from app.app import app as flask_app


class TestGetDb:
    def test_returns_connection(self) -> None:
        with flask_app.app_context():
            db = app_module.get_db()
            assert db is not None

    def test_returns_same_connection_on_second_call(self) -> None:
        with flask_app.app_context():
            db1 = app_module.get_db()
            db2 = app_module.get_db()
            assert db1 is db2

    def test_row_factory_is_sqlite_row(self) -> None:
        with flask_app.app_context():
            db = app_module.get_db()
            assert db.row_factory == sqlite3.Row


class TestCloseDb:
    def test_closes_existing_connection(self) -> None:
        # get_db() sets g.db; close_db is called automatically on context exit
        with flask_app.app_context():
            app_module.get_db()
        # No exception means the connection was closed cleanly

    def test_no_error_when_no_connection_was_opened(self) -> None:
        # close_db must handle g.db being absent (db is None branch)
        with flask_app.app_context():
            pass  # never call get_db; teardown still fires


class TestInitDb:
    def test_creates_todos_table(self) -> None:
        with flask_app.app_context():
            app_module.init_db()
            db = app_module.get_db()
            rows = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='todos'"
            ).fetchall()
            assert len(rows) == 1

    def test_is_idempotent(self) -> None:
        with flask_app.app_context():
            app_module.init_db()
            app_module.init_db()  # CREATE TABLE IF NOT EXISTS must not raise
