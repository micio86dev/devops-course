"""ORM models.

A single ``Todo`` table backs the app. ``done`` stays an integer (0/1) on
purpose, matching the existing wire contract — flipping it to a Python
``bool`` would break ``SPEC.md`` DB-04 and every API test that asserts
``data["done"] == 0``.
"""

from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Todo(Base):
    __tablename__ = "todos"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(1024), nullable=False)
    done: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "done": self.done,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
