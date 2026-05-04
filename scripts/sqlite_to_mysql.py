"""One-shot data migration: SQLite todos -> Managed MySQL.

Reads the source SQLite file from ``DATABASE_PATH`` and the destination
MySQL connection from the same ``DB_*`` env vars the app uses
(``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD``,
``DB_SSL_CA``). The script never mutates the source — SQLite is opened
read-only via the ``mode=ro`` URI flag.

Designed to be run from one of the app droplets after Terraform
provisions the new cluster and before flipping the deploy. It does not
run automatically anywhere — see ``docs/MYSQL_MIGRATION.md``.

Usage::

    python scripts/sqlite_to_mysql.py [--dry-run] [--truncate]
                                      [--batch-size N]

``--dry-run``  Skip the inserts; print source/dest counts only.
``--truncate`` ``DELETE FROM todos`` on the destination first
               (idempotent re-runs).
``--batch-size`` Tune ``executemany`` batch size (default 500).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections.abc import Iterator
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

REQUIRED_ENVS = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
SOURCE_PATH_ENV = "DATABASE_PATH"


def _check_env() -> str:
    """Validate required envs and return the SQLite source path."""
    missing = [k for k in REQUIRED_ENVS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
    src = os.environ.get(SOURCE_PATH_ENV, "").strip()
    if not src:
        raise SystemExit(f"{SOURCE_PATH_ENV} must point at the SQLite file")
    if not os.path.isfile(src):
        raise SystemExit(f"SQLite source file not found: {src}")
    return src


def _connect_mysql() -> pymysql.connections.Connection[DictCursor]:
    """Open a PyMySQL connection using the same env contract as the app."""
    ssl_ca = os.environ.get("DB_SSL_CA", "").strip()
    ssl: dict[str, str] | None = {"ca": ssl_ca} if ssl_ca and os.path.isfile(ssl_ca) else None
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT") or "3306"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        ssl=ssl,
        autocommit=False,
    )


def _ensure_schema(mysql_conn: pymysql.connections.Connection[DictCursor]) -> None:
    """Create the ``todos`` table on MySQL if it doesn't exist (matches app/models.py)."""
    with mysql_conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
              id         BIGINT        NOT NULL AUTO_INCREMENT,
              text       VARCHAR(1024) NOT NULL,
              done       SMALLINT      NOT NULL DEFAULT 0,
              created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )
    mysql_conn.commit()


def _iter_source_rows(src: sqlite3.Connection, batch: int) -> Iterator[list[tuple[Any, ...]]]:
    """Yield rows from SQLite in fixed-size batches."""
    cur = src.execute("SELECT id, text, done, created_at FROM todos ORDER BY id")
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            return
        yield [tuple(r) for r in rows]


def _count(conn: sqlite3.Connection | pymysql.connections.Connection[DictCursor]) -> int:
    """Return COUNT(*) from todos on either backend."""
    if isinstance(conn, sqlite3.Connection):
        result = conn.execute("SELECT COUNT(*) FROM todos").fetchone()
        return int(result[0])
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM todos")
        row = cur.fetchone()
    return int(row["n"]) if row else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--dry-run", action="store_true", help="don't insert; just verify counts")
    p.add_argument("--truncate", action="store_true", help="DELETE FROM todos before insert")
    p.add_argument(
        "--batch-size", type=int, default=500, help="executemany batch size (default 500)"
    )
    args = p.parse_args(argv)

    src_path = _check_env()
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst = _connect_mysql()
    try:
        _ensure_schema(dst)
        src_n = _count(src)
        dst_n_before = _count(dst)
        dst_label = f"{os.environ['DB_HOST']}/{os.environ['DB_NAME']}"
        print(f"source rows: {src_n}  ({src_path})")
        print(f"dest   rows (before): {dst_n_before}  ({dst_label})")

        if args.dry_run:
            print("dry-run: skipping inserts")
            return 0

        with dst.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            if args.truncate:
                cur.execute("DELETE FROM todos")

            inserted = 0
            for batch in _iter_source_rows(src, args.batch_size):
                cur.executemany(
                    "INSERT INTO todos (id, text, done, created_at) VALUES (%s, %s, %s, %s)",
                    batch,
                )
                inserted += len(batch)
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        dst.commit()

        dst_n_after = _count(dst)
        print(f"inserted: {inserted}")
        print(f"dest   rows (after):  {dst_n_after}")
        if dst_n_after != src_n + (0 if args.truncate else dst_n_before):
            dst.rollback()
            print("ERROR: row count mismatch — rolled back", file=sys.stderr)
            return 1
        print("OK: row counts consistent")
        return 0
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    raise SystemExit(main())
