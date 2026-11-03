"""Yazma geri bildirimi. Türkçe açıklama saklanmaz; `content.error_tags`'tan okunur."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        CheckConstraint("status IN ('shown','rejected','deferred')", name="status"),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Öğrencinin metni bu olayın payload'unda durur; burada kopyası yok.
    writing_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{LEARNING}.events.id"), index=True
    )
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.llm_calls.id"))
    status: Mapped[str] = mapped_column(String(16))
    hint_tr: Mapped[str | None] = mapped_column(Text)
    # Doğru cümle; öğrenci yeniden yazdıktan sonra gösterilir.
    correction: Mapped[str | None] = mapped_column(Text)
    validator_result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()


class ErrorMark(Base):
    """Bulunan her hata; en fazla 2'si `shown`. Hata örüntüleri buradan türetilir."""

    __tablename__ = "error_marks"
    __table_args__ = {"schema": LEARNING}

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(
        ForeignKey(f"{LEARNING}.feedbacks.id", ondelete="CASCADE"), index=True
    )
    tag_code: Mapped[str] = mapped_column(ForeignKey("content.error_tags.code"), index=True)
    span_start: Mapped[int] = mapped_column(SmallInteger)
    span_end: Mapped[int] = mapped_column(SmallInteger)
    shown: Mapped[bool]
