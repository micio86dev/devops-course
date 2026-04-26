"""Unit tests for Flask route handler functions.

Each test calls the handler function directly — no HTTP client, no routing layer.
get_db() is mocked so these tests verify internal logic (SQL strings, parameter
binding, commit calls) in complete isolation from the database.
"""
import json
from unittest.mock import MagicMock, patch

import app as app_module
from app import app as flask_app


def _row(**kwargs):
    """Minimal todo dict that survives dict(r) and jsonify()."""
    base = {"id": 1, "text": "Test", "done": 0, "created_at": "2024-01-01 00:00:00"}
    return base | kwargs


class TestIndex:
    def test_renders_index_template(self):
        with flask_app.test_request_context("/"):
            with patch("app.render_template", return_value="<html>") as mock_render:
                app_module.index()
        mock_render.assert_called_once_with("index.html")


class TestHealth:
    def test_returns_200_with_ok_payload(self):
        with flask_app.app_context():
            response, status = app_module.health()
        assert status == 200
        assert json.loads(response.get_data()) == {"status": "ok"}


class TestListTodos:
    def test_query_orders_by_created_at_then_id_desc(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.list_todos()
        sql = mock_db.execute.call_args[0][0]
        assert "ORDER BY created_at DESC, id DESC" in sql

    def test_returns_serialized_rows(self):
        rows = [_row(id=1), _row(id=2)]
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = rows
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                response = app_module.list_todos()
        assert json.loads(response.get_data()) == rows


class TestCreateTodo:
    def _mock_db(self, todo_row):
        insert_cur = MagicMock()
        insert_cur.lastrowid = todo_row["id"]
        select_cur = MagicMock()
        select_cur.fetchone.return_value = todo_row
        mock_db = MagicMock()
        mock_db.execute.side_effect = [insert_cur, select_cur]
        return mock_db

    def test_inserts_stripped_text(self):
        mock_db = self._mock_db(_row(text="Buy milk"))
        with flask_app.test_request_context(
            "/api/todos", method="POST", json={"text": "  Buy milk  "}
        ):
            with patch("app.get_db", return_value=mock_db):
                app_module.create_todo()
        insert_params = mock_db.execute.call_args_list[0][0][1]
        assert insert_params == ("Buy milk",)

    def test_commits_after_insert(self):
        mock_db = self._mock_db(_row())
        with flask_app.test_request_context(
            "/api/todos", method="POST", json={"text": "Task"}
        ):
            with patch("app.get_db", return_value=mock_db):
                app_module.create_todo()
        mock_db.commit.assert_called_once()

    def test_fetches_inserted_row_by_lastrowid(self):
        mock_db = self._mock_db(_row(id=42))
        with flask_app.test_request_context(
            "/api/todos", method="POST", json={"text": "Task"}
        ):
            with patch("app.get_db", return_value=mock_db):
                app_module.create_todo()
        select_params = mock_db.execute.call_args_list[1][0][1]
        assert 42 in select_params


class TestToggleTodo:
    def _mock_db(self, result_row):
        update_cur = MagicMock()
        select_cur = MagicMock()
        select_cur.fetchone.return_value = result_row
        mock_db = MagicMock()
        mock_db.execute.side_effect = [update_cur, select_cur]
        return mock_db

    def test_update_sql_uses_not_done_expression(self):
        mock_db = self._mock_db(_row(done=1))
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.toggle_todo(1)
        update_sql = mock_db.execute.call_args_list[0][0][0]
        assert "NOT done" in update_sql

    def test_passes_todo_id_to_update(self):
        mock_db = self._mock_db(_row(id=7, done=1))
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.toggle_todo(7)
        update_params = mock_db.execute.call_args_list[0][0][1]
        assert 7 in update_params

    def test_commits_after_update(self):
        mock_db = self._mock_db(_row(done=1))
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.toggle_todo(1)
        mock_db.commit.assert_called_once()

    def test_returns_404_when_row_is_none(self):
        mock_db = self._mock_db(None)
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                response, status = app_module.toggle_todo(9999)
        assert status == 404
        assert json.loads(response.get_data()) == {"error": "not found"}


class TestDeleteTodo:
    def test_delete_sql_targets_correct_id(self):
        mock_db = MagicMock()
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.delete_todo(5)
        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        assert "DELETE FROM todos" in sql
        assert 5 in params

    def test_commits_after_delete(self):
        mock_db = MagicMock()
        with flask_app.app_context():
            with patch("app.get_db", return_value=mock_db):
                app_module.delete_todo(3)
        mock_db.commit.assert_called_once()
