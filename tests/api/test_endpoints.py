"""API tests — HTTP endpoints via Flask test client.

Each test hits a real endpoint through the full Flask request/response cycle.
The DB is a real SQLite file (tests/test.db); the clean_db autouse fixture
in tests/conftest.py truncates it before every test.
"""

from typing import Any, cast

from flask.testing import FlaskClient

import app.app as app_module
from app.app import app as flask_app


class TestIndex:
    def test_returns_200(self, client: FlaskClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html_content(self, client: FlaskClient) -> None:
        resp = client.get("/")
        assert b"html" in resp.data.lower()


class TestHealth:
    def test_returns_200(self, client: FlaskClient) -> None:
        resp = client.get("/healthz")
        assert resp.status_code == 200

    def test_returns_ok_payload(self, client: FlaskClient) -> None:
        data = client.get("/healthz").get_json()
        assert data == {"status": "ok"}


class TestListTodos:
    def test_empty_database_returns_empty_list(self, client: FlaskClient) -> None:
        resp = client.get("/api/todos")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_all_todos(self, client: FlaskClient) -> None:
        client.post("/api/todos", json={"text": "First"})
        client.post("/api/todos", json={"text": "Second"})
        todos = client.get("/api/todos").get_json()
        assert len(todos) == 2

    def test_ordered_by_created_at_desc(self, client: FlaskClient) -> None:
        # Insert with explicit timestamps to make ordering deterministic
        with flask_app.app_context():
            db = app_module.get_db()
            db.execute(
                "INSERT INTO todos (text, created_at) VALUES (?, ?)",
                ("Older", "2024-01-01 00:00:01"),
            )
            db.execute(
                "INSERT INTO todos (text, created_at) VALUES (?, ?)",
                ("Newer", "2024-01-01 00:00:02"),
            )
            db.commit()

        todos = client.get("/api/todos").get_json()
        assert todos[0]["text"] == "Newer"
        assert todos[1]["text"] == "Older"

    def test_id_desc_tiebreaker_for_same_second(self, client: FlaskClient) -> None:
        # Two rows with identical created_at: higher id must appear first
        with flask_app.app_context():
            db = app_module.get_db()
            db.execute(
                "INSERT INTO todos (text, created_at) VALUES (?, ?)",
                ("First inserted", "2024-01-01 00:00:00"),
            )
            db.execute(
                "INSERT INTO todos (text, created_at) VALUES (?, ?)",
                ("Second inserted", "2024-01-01 00:00:00"),
            )
            db.commit()

        todos = client.get("/api/todos").get_json()
        assert todos[0]["text"] == "Second inserted"
        assert todos[1]["text"] == "First inserted"


class TestCreateTodo:
    def test_valid_text_returns_201(self, client: FlaskClient) -> None:
        resp = client.post("/api/todos", json={"text": "Buy milk"})
        assert resp.status_code == 201

    def test_response_contains_todo_fields(self, client: FlaskClient) -> None:
        data = client.post("/api/todos", json={"text": "Buy milk"}).get_json()
        assert data["text"] == "Buy milk"
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["done"] == 0

    def test_response_includes_created_at(self, client: FlaskClient) -> None:
        data = client.post("/api/todos", json={"text": "Timestamped"}).get_json()
        assert "created_at" in data
        assert data["created_at"] is not None

    def test_strips_surrounding_whitespace(self, client: FlaskClient) -> None:
        data = client.post("/api/todos", json={"text": "  Buy milk  "}).get_json()
        assert data["text"] == "Buy milk"

    def test_empty_text_returns_400(self, client: FlaskClient) -> None:
        resp = client.post("/api/todos", json={"text": ""})
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "text is required"}

    def test_whitespace_only_text_returns_400(self, client: FlaskClient) -> None:
        resp = client.post("/api/todos", json={"text": "   "})
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "text is required"}

    def test_missing_text_field_returns_400(self, client: FlaskClient) -> None:
        resp = client.post("/api/todos", json={})
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "text is required"}

    def test_non_json_body_returns_400(self, client: FlaskClient) -> None:
        resp = client.post("/api/todos", data="not json", content_type="text/plain")
        assert resp.status_code == 400
        assert resp.get_json() == {"error": "text is required"}


class TestToggleTodo:
    def _create(self, client: FlaskClient, text: str = "Test todo") -> int:
        return cast(int, client.post("/api/todos", json={"text": text}).get_json()["id"])

    def test_toggles_done_false_to_true(self, client: FlaskClient) -> None:
        todo_id = self._create(client)
        data = client.patch(f"/api/todos/{todo_id}/toggle").get_json()
        assert data["done"] == 1

    def test_toggles_done_true_to_false(self, client: FlaskClient) -> None:
        todo_id = self._create(client)
        client.patch(f"/api/todos/{todo_id}/toggle")  # → 1
        data = client.patch(f"/api/todos/{todo_id}/toggle").get_json()  # → 0
        assert data["done"] == 0

    def test_returns_200_with_todo_data(self, client: FlaskClient) -> None:
        todo_id = self._create(client, "Check me")
        resp = client.patch(f"/api/todos/{todo_id}/toggle")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == todo_id

    def test_nonexistent_id_returns_404(self, client: FlaskClient) -> None:
        resp = client.patch("/api/todos/9999/toggle")
        assert resp.status_code == 404
        assert resp.get_json() == {"error": "not found"}


class TestDeleteTodo:
    def _create(self, client: FlaskClient, text: str = "Delete me") -> int:
        return cast(int, client.post("/api/todos", json={"text": text}).get_json()["id"])

    def test_returns_204_no_content(self, client: FlaskClient) -> None:
        todo_id = self._create(client)
        resp = client.delete(f"/api/todos/{todo_id}")
        assert resp.status_code == 204
        assert resp.data == b""

    def test_todo_is_removed_from_list(self, client: FlaskClient) -> None:
        todo_id = self._create(client)
        client.delete(f"/api/todos/{todo_id}")
        todos: list[Any] = client.get("/api/todos").get_json()
        assert not any(t["id"] == todo_id for t in todos)

    def test_nonexistent_id_returns_204(self, client: FlaskClient) -> None:
        resp = client.delete("/api/todos/9999")
        assert resp.status_code == 204
