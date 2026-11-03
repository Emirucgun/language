import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class Curriculum(Base):
    """Müfredat ajanının önerip kural katmanının onayladığı plan; her yeniden plan yeni sürüm."""

    __tablename__ = "curricula"
    __table_args__ = (
        Index(None, "user_id", "version", unique=True),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    version: Mapped[int]
    weeks: Mapped[list[Any]] = mapped_column(JSONB)
    skill_weights: Mapped[dict[str, Any]] = mapped_column(JSONB)
    change_reason: Mapped[str | None] = mapped_column(Text)
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.llm_calls.id"))
    created_at: Mapped[datetime] = created_at_column()
