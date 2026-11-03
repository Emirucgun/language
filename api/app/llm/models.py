"""LLM çağrı kaydı ve LLM'e giden öğrenci özeti.

Prompt metni saklanmaz: prompt dosyası sürümü + öğrenci özeti + görev girdisi
(activity_contents / events) ile her çağrı yeniden kurulabilir.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class LearnerSnapshot(Base):
    """Olaylardan deterministik üretilen, günde bir donan kısa öğrenci özeti."""

    __tablename__ = "learner_snapshots"
    __table_args__ = (
        Index(None, "user_id", "content_hash", unique=True),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    content_hash: Mapped[bytes] = mapped_column(LargeBinary(32))
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int]
    # Özetin hesaplandığı son olay: aynı girdiden aynı özet çıkar.
    last_event_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_column()


class LlmCall(Base):
    __tablename__ = "llm_calls"
    __table_args__ = (
        # Kullanıcı başına günlük çağrı limiti bu indeksle sayılır.
        Index(None, "user_id", "created_at"),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    purpose: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.learner_snapshots.id"))
    input_tokens: Mapped[int | None]
    cache_read_tokens: Mapped[int | None]
    cache_write_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(16))
    stop_reason: Mapped[str | None] = mapped_column(String(32))
    cost_microusd: Mapped[int | None] = mapped_column(BigInteger)
    # Ham yanıt yalnızca doğrulama/ayrıştırma hatasında saklanır, 30 gün sonra temizlenir.
    raw_on_failure: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
