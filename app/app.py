import os
import sqlite3
from typing import Any, cast

from flask import Flask, Response, g, jsonify, render_template, request

app = Flask(__name__)

DATABASE = os.environ.get("DATABASE_PATH", "/data/todos.db")


# ── DB helpers ───────────────────────────────────────────────────────────────


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return cast(sqlite3.Connection, g.db)


@app.teardown_appcontext
def close_db(error: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            text      TEXT    NOT NULL,
            done      BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


# ── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/healthz")
def health() -> tuple[Response, int]:
    """Liveness probe used by Docker and the orchestrator."""
    return jsonify({"status": "ok"}), 200


@app.route("/api/todos", methods=["GET"])
def list_todos() -> Response:
    rows = get_db().execute("SELECT * FROM todos ORDER BY created_at DESC, id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/todos", methods=["POST"])
def create_todo() -> tuple[Response, int]:
    raw: Any = request.get_json(silent=True)
    body: dict[str, Any] = raw if isinstance(raw, dict) else {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    cur = db.execute("INSERT INTO todos (text) VALUES (?)", (text,))
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/todos/<int:todo_id>/toggle", methods=["PATCH"])
def toggle_todo(todo_id: int) -> tuple[Response, int]:
    db = get_db()
    db.execute("UPDATE todos SET done = NOT done WHERE id = ?", (todo_id,))
    db.commit()
    row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row)), 200


@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id: int) -> tuple[str, int]:
    db = get_db()
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    return "", 204


# ── DB initialisation ────────────────────────────────────────────────────────
# Module-level: runs under both gunicorn (import) and flask run.
with app.app_context():
    init_db()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
