import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class WeeklyReport(Base):
    """Türev; kullanıcının gördüğü hal saklanır, olaylardan yeniden üretilebilir."""

    __tablename__ = "weekly_reports"
    __table_args__ = (
        Index(None, "user_id", "week_start", unique=True),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    week_start: Mapped[date]
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = created_at_column()


class Review(Base):
    """Işıl'ın örneklem denetimi ve "sorun var" kuyruğu (H4)."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("target_type IN ('activity_content','feedback')", name="target_type"),
        CheckConstraint("verdict IN ('ok','minor','wrong')", name="verdict"),
        Index(None, "target_type", "target_id"),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[int]
    reviewer: Mapped[str] = mapped_column(String(64))
    verdict: Mapped[str] = mapped_column(String(8))
    wrong_teaching: Mapped[bool]
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
