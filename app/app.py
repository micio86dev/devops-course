import os
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import delete, select

from app.db import build_connect_args, build_database_uri, db
from app.models import Todo

# ── OpenTelemetry setup ──────────────────────────────────────────────────────
# OTLP_ENDPOINT: empty string disables tracing (no-op provider).
# Dev default: http://tempo:4317 (docker-compose network name).
# Production: set to http://<monitoring_node_private_ip>:4317 via .env.monitoring.
_otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://tempo:4317")
provider = TracerProvider(
    sampler=ALWAYS_ON, resource=Resource.create({"service.name": "flask-todo"})
)
if _otlp_endpoint:  # pragma: no cover
    exporter = OTLPSpanExporter(endpoint=_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# inietta trace_id/span_id automaticamente in tutti i log
LoggingInstrumentor().instrument(set_logging_format=True)

# ── App ──────────────────────────────────────────────────────────────────────
app = Flask(__name__)
metrics = PrometheusMetrics(app)
FlaskInstrumentor().instrument_app(app)  # type: ignore[no-untyped-call]
SQLAlchemyInstrumentor().instrument()

app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": build_connect_args(),
    # Without pre-ping, idle connections silently dropped by the managed
    # database / load balancer surface as one failed request after a quiet
    # period. The extra round trip per checkout is cheap insurance.
    "pool_pre_ping": True,
}

db.init_app(app)


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
    rows = (
        db.session.execute(select(Todo).order_by(Todo.created_at.desc(), Todo.id.desc()))
        .scalars()
        .all()
    )
    return jsonify([t.to_dict() for t in rows])


@app.route("/api/todos", methods=["POST"])
def create_todo() -> tuple[Response, int]:
    raw: Any = request.get_json(silent=True)
    body: dict[str, Any] = raw if isinstance(raw, dict) else {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    todo = Todo(text=text)
    db.session.add(todo)
    db.session.commit()
    # Pull the server-populated created_at back into the instance so to_dict()
    # has a real datetime to format.
    db.session.refresh(todo)
    return jsonify(todo.to_dict()), 201


@app.route("/api/todos/<int:todo_id>/toggle", methods=["PATCH"])
def toggle_todo(todo_id: int) -> tuple[Response, int]:
    todo = db.session.get(Todo, todo_id)
    if todo is None:
        return jsonify({"error": "not found"}), 404
    todo.done = 1 - todo.done
    db.session.commit()
    db.session.refresh(todo)
    return jsonify(todo.to_dict()), 200


@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id: int) -> tuple[str, int]:
    db.session.execute(delete(Todo).where(Todo.id == todo_id))
    db.session.commit()
    return "", 204


# ── DB initialisation ────────────────────────────────────────────────────────
# Module-level: runs under both gunicorn (import) and flask run.
# create_all() is idempotent — it issues CREATE TABLE IF NOT EXISTS, so
# repeated imports / restarts never reset data.
with app.app_context():
    db.create_all()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
