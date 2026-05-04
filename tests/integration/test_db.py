"""Integration tests — SQLAlchemy data layer against real MySQL.

These tests assume a reachable MySQL server (compose service `mysql`
locally, mysql:8 service container in CI). The clean_db autouse fixture
in tests/conftest.py truncates rows between tests; the schema is created
once at module import via app.app's module-level db.create_all().
"""

from sqlalchemy import inspect, select

from app.app import app as flask_app
from app.db import db
from app.models import Todo


class TestSchema:
    def test_todos_table_exists(self) -> None:
        with flask_app.app_context():
            inspector = inspect(db.engine)
            assert "todos" in inspector.get_table_names()

    def test_create_all_is_idempotent(self) -> None:
        # CREATE TABLE IF NOT EXISTS — calling twice must not raise.
        with flask_app.app_context():
            db.create_all()
            db.create_all()


class TestSession:
    def test_round_trips_a_todo(self) -> None:
        with flask_app.app_context():
            todo = Todo(text="round trip")
            db.session.add(todo)
            db.session.commit()
            db.session.refresh(todo)
            fetched = db.session.execute(select(Todo).where(Todo.id == todo.id)).scalar_one()
            assert fetched.text == "round trip"
            assert fetched.done == 0

    def test_default_done_is_zero(self) -> None:
        with flask_app.app_context():
            todo = Todo(text="default done")
            db.session.add(todo)
            db.session.commit()
            db.session.refresh(todo)
            assert todo.done == 0

    def test_created_at_is_populated_by_server_default(self) -> None:
        with flask_app.app_context():
            todo = Todo(text="timestamped")
            db.session.add(todo)
            db.session.commit()
            db.session.refresh(todo)
            assert todo.created_at is not None
