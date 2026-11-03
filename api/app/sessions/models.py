"""Günlük oturum, üretilen içerik ve içeriğin kullanıcıya gösterimi.

Üretilen içerik `activity_contents`'te bir kez saklanır; `activities` yalnızca
"bu içerik bu kullanıcıya gösterildi" bilgisini tutar.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column

ACTIVITY_KINDS = "('recall','new_item','reading','listening','writing','dialogue')"


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('pending','ready','failed','completed')", name="status"),
        Index(None, "user_id", "local_date", unique=True),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    local_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.learner_snapshots.id"))
    created_at: Mapped[datetime] = created_at_column()


class ActivityContent(Base):
    """Doğrulanmış içeriğin tek kopyası; `shareable` ise başka kullanıcılara da gösterilebilir."""

    __tablename__ = "activity_contents"
    __table_args__ = (
        CheckConstraint(f"kind IN {ACTIVITY_KINDS}", name="kind"),
        CheckConstraint("status IN ('approved','rejected','retired')", name="status"),
        # Paylaşım yalnızca kısa türlerde (kullanıcı kararı, 3 Kas 2026).
        CheckConstraint("NOT shareable OR kind IN ('recall','new_item')", name="shareable_kinds"),
        # Yeniden kullanım araması: önce LLM'siz eşleşme denenir.
        Index(
            "ix_activity_contents_reuse",
            "kind",
            "cefr_sub",
            "interest_tag",
            postgresql_where=text("status = 'approved' AND shareable"),
        ),
        Index("ix_activity_contents_item_ids", "item_ids", postgresql_using="gin"),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    kind: Mapped[str] = mapped_column(String(16))
    item_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    cefr_sub: Mapped[str] = mapped_column(String(8))
    interest_tag: Mapped[str | None] = mapped_column(String(32))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    audio_key: Mapped[str | None] = mapped_column(String(256))
    # Şablonla üretilen içerikte model ve LLM çağrısı yoktur.
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    validator_version: Mapped[str] = mapped_column(String(16))
    validator_result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16))
    shareable: Mapped[bool] = mapped_column(server_default="false")
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey(f"{LEARNING}.llm_calls.id"))
    created_at: Mapped[datetime] = created_at_column()


class Activity(Base):
    """Bir içeriğin bir kullanıcıya gösterimi. Aynı içerik aynı kişiye bir kez gelir."""

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("origin IN ('session','extra','template')", name="origin"),
        Index(None, "user_id", "content_id", unique=True),
        {"schema": LEARNING},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{LEARNING}.study_sessions.id"), index=True
    )
    content_id: Mapped[int] = mapped_column(ForeignKey(f"{LEARNING}.activity_contents.id"))
    origin: Mapped[str] = mapped_column(String(16))
    recommended: Mapped[bool]
    position: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = created_at_column()
