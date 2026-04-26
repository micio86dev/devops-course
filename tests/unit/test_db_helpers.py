"""Unit tests for DB helper functions.

All external dependencies (sqlite3, os.makedirs) are mocked so these tests
run without any filesystem I/O and verify the exact API calls made.
"""
import os
import sqlite3
from unittest.mock import MagicMock, patch

import app as app_module
from app import app as flask_app


class TestGetDb:
    def test_creates_parent_directory(self):
        with flask_app.app_context():
            with patch("app.os.makedirs") as mock_makedirs, \
                 patch("app.sqlite3.connect", return_value=MagicMock()):
                app_module.get_db()
        mock_makedirs.assert_called_once_with(
            os.path.dirname(app_module.DATABASE), exist_ok=True
        )

    def test_opens_connection_to_database_path(self):
        with flask_app.app_context():
            with patch("app.os.makedirs"), \
                 patch("app.sqlite3.connect", return_value=MagicMock()) as mock_connect:
                app_module.get_db()
        mock_connect.assert_called_once_with(
            app_module.DATABASE, detect_types=sqlite3.PARSE_DECLTYPES
        )

    def test_sets_row_factory_to_sqlite_row(self):
        mock_conn = MagicMock()
        with flask_app.app_context():
            with patch("app.os.makedirs"), \
                 patch("app.sqlite3.connect", return_value=mock_conn):
                app_module.get_db()
        assert mock_conn.row_factory == sqlite3.Row

    def test_caches_connection_on_repeated_calls(self):
        with flask_app.app_context():
            with patch("app.os.makedirs"), \
                 patch("app.sqlite3.connect", return_value=MagicMock()) as mock_connect:
                first = app_module.get_db()
                second = app_module.get_db()
        assert first is second
        assert mock_connect.call_count == 1


class TestCloseDb:
    def test_calls_close_on_existing_connection(self):
        mock_conn = MagicMock()
        with flask_app.app_context():
            with patch("app.os.makedirs"), \
                 patch("app.sqlite3.connect", return_value=mock_conn):
                app_module.get_db()
        # app_context exit triggers close_db via teardown_appcontext
        mock_conn.close.assert_called_once()

    def test_does_not_raise_without_a_connection(self):
        with flask_app.app_context():
            pass  # close_db fires on teardown without any get_db call

    def test_accepts_none_as_error_argument(self):
        with flask_app.app_context():
            app_module.close_db(None)

    def test_accepts_exception_as_error_argument(self):
        with flask_app.app_context():
            app_module.close_db(RuntimeError("database gone"))


class TestInitDb:
    def test_executes_create_table_if_not_exists(self):
        with flask_app.app_context():
            mock_conn = MagicMock()
            with patch("app.get_db", return_value=mock_conn):
                app_module.init_db()
        sql = mock_conn.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS todos" in sql

    def test_schema_includes_all_columns(self):
        with flask_app.app_context():
            mock_conn = MagicMock()
            with patch("app.get_db", return_value=mock_conn):
                app_module.init_db()
        sql = mock_conn.execute.call_args[0][0]
        for column in ("id", "text", "done", "created_at"):
            assert column in sql

    def test_commits_after_schema_creation(self):
        with flask_app.app_context():
            mock_conn = MagicMock()
            with patch("app.get_db", return_value=mock_conn):
                app_module.init_db()
        mock_conn.commit.assert_called_once()
