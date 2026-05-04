"""SQLAlchemy setup for the todo app.

This module owns:
- the declarative ``Base`` (typed via SQLAlchemy 2.0 ``Mapped[]``);
- the ``db`` Flask-SQLAlchemy extension, bound to ``Base``;
- two pure helpers that translate environment variables into the
  ``SQLALCHEMY_DATABASE_URI`` and the ``connect_args`` consumed by the
  underlying engine.

Connection details come from ``DB_HOST``/``DB_PORT``/``DB_NAME``/``DB_USER``/
``DB_PASSWORD``. SSL is opt-in via ``DB_SSL_CA``: when it points at a
readable file (production), TLS is enabled with that CA cert; when it is
empty or missing (local dev / CI service container), the connection is
plain TCP.
"""

import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import URL
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single declarative base shared by every ORM model in the app."""


db = SQLAlchemy(model_class=Base)


def build_database_uri() -> URL:
    """Build the SQLAlchemy ``URL`` from the ``DB_*`` environment variables.

    ``DB_PORT`` defaults to ``3306``; every other variable is required.
    """
    return URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT") or "3306"),
        database=os.environ["DB_NAME"],
        query={"charset": "utf8mb4"},
    )


def build_connect_args() -> dict[str, object]:
    """Return the ``connect_args`` for the engine.

    Enables TLS only when ``DB_SSL_CA`` is set and points at a readable
    file. DigitalOcean Managed MySQL requires TLS; the local ``mysql:8``
    service container does not — leaving ``DB_SSL_CA`` empty disables it.
    """
    ca = os.environ.get("DB_SSL_CA", "").strip()
    if ca and os.path.isfile(ca):
        return {"ssl": {"ca": ca}}
    return {}
