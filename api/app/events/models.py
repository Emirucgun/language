"""Tek doğruluk kaynağı.

Satırlar yalnızca eklenir; uygulama rolünün UPDATE/DELETE yetkisi yoktur.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 4", name="rating"),
        Index(None, "user_id", "recorded_at"),
        Index(None, "user_id", "item_id"),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    type: Mapped[str] = mapped_column(String(32))
    # İstemcinin bildirdiği an; sıralama ve yeniden oynatma `id` ile yapılır.
    occurred_at: Mapped[datetime]
    recorded_at: Mapped[datetime] = created_at_column()
    activity_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.activities.id"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("content.items.id"))
    # FSRS derecesi (Again=1 … Easy=4); tekrar motoru yalnızca bunu okur.
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    schema_version: Mapped[int] = mapped_column(SmallInteger, server_default="1")
