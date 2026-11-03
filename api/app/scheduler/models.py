import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base


class ItemState(Base):
    """Türev FSRS durumu; her an `events`'ten yeniden hesaplanabilir."""

    __tablename__ = "item_states"
    __table_args__ = (
        Index(None, "user_id", "due"),
        {"schema": LEARNING},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("content.items.id"), primary_key=True)
    state: Mapped[int] = mapped_column(SmallInteger)
    step: Mapped[int | None] = mapped_column(SmallInteger)
    stability: Mapped[float | None]
    difficulty: Mapped[float | None]
    due: Mapped[datetime]
    last_review: Mapped[datetime | None]
    reps: Mapped[int] = mapped_column(server_default="0")
    lapses: Mapped[int] = mapped_column(server_default="0")
    # Filigran: bu duruma işlenmiş son olay. Artımlı güncelleme buradan devam eder.
    last_event_id: Mapped[int] = mapped_column(BigInteger)
