"""Unit tests for app.db helpers — env-var parsing only.

These tests don't touch the network or a database. They verify that
build_database_uri() and build_connect_args() correctly translate the
DB_* environment variables into the SQLAlchemy URL and connect_args.
"""

import tempfile

import pytest

from app.db import build_connect_args, build_database_uri


class TestBuildDatabaseUri:
    def test_uses_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "h.example")
        monkeypatch.setenv("DB_PORT", "1234")
        monkeypatch.setenv("DB_NAME", "n")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")

        url = build_database_uri()

        assert url.host == "h.example"
        assert url.port == 1234
        assert url.database == "n"
        assert url.username == "u"
        assert url.password == "p"

    def test_drivername_is_mysql_pymysql(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "h")
        monkeypatch.setenv("DB_NAME", "n")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")

        url = build_database_uri()

        assert url.drivername == "mysql+pymysql"

    def test_default_port_is_3306(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "h")
        monkeypatch.setenv("DB_NAME", "n")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.delenv("DB_PORT", raising=False)

        url = build_database_uri()

        assert url.port == 3306

    def test_empty_db_port_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "h")
        monkeypatch.setenv("DB_NAME", "n")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("DB_PORT", "")

        url = build_database_uri()

        assert url.port == 3306

    def test_charset_query_is_utf8mb4(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "h")
        monkeypatch.setenv("DB_NAME", "n")
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")

        url = build_database_uri()

        assert url.query.get("charset") == "utf8mb4"


class TestBuildConnectArgs:
    def test_no_ssl_when_db_ssl_ca_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DB_SSL_CA", raising=False)
        assert build_connect_args() == {}

    def test_no_ssl_when_db_ssl_ca_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_SSL_CA", "")
        assert build_connect_args() == {}

    def test_no_ssl_when_db_ssl_ca_only_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_SSL_CA", "   ")
        assert build_connect_args() == {}

    def test_no_ssl_when_path_does_not_exist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_SSL_CA", "/nonexistent/path/to/ca.pem")
        assert build_connect_args() == {}

    def test_ssl_set_when_path_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pem") as tmp:
            monkeypatch.setenv("DB_SSL_CA", tmp.name)
            assert build_connect_args() == {"ssl": {"ca": tmp.name}}
