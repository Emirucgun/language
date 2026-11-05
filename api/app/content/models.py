"""Küratörlü içerik: öğe havuzu, izinli kelimeler, hata etiketleri, sabit testler.

Uygulama rolü bu şemayı yalnızca okur; içerik içe aktarma betikleriyle yazılır.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import CONTENT, Base

CEFR_LEVELS = "('A1','A2','B1','B2','C1','C2')"


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("kind IN ('word','chunk','structure')", name="kind"),
        CheckConstraint(f"cefr IN {CEFR_LEVELS}", name="cefr"),
        Index(None, "cefr", "active"),
        {"schema": CONTENT},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16))
    text_en: Mapped[str] = mapped_column(Text)
    text_tr: Mapped[str] = mapped_column(Text)
    cefr: Mapped[str] = mapped_column(String(2))
    sublevel: Mapped[int | None]
    # Doğrulayıcı için çekimli biçimler ("go" -> goes, went, gone, going).
    forms: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    topics: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    source_list: Mapped[str | None] = mapped_column(String(64))
    error_risk_notes: Mapped[str | None] = mapped_column(Text)
    reference_sentences: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    active: Mapped[bool] = mapped_column(server_default="true")


class VocabAllowlist(Base):
    __tablename__ = "vocab_allowlist"
    __table_args__ = (
        CheckConstraint(f"cefr IN {CEFR_LEVELS}", name="cefr"),
        {"schema": CONTENT},
    )

    lemma: Mapped[str] = mapped_column(Text, primary_key=True)
    cefr: Mapped[str] = mapped_column(String(2))
    forms: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    source: Mapped[str] = mapped_column(String(64))


class ErrorTag(Base):
    """Türkçe hata açıklamalarının tek kaynağı; LLM yalnızca `code` seçer."""

    __tablename__ = "error_tags"
    __table_args__ = {"schema": CONTENT}

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name_tr: Mapped[str] = mapped_column(Text)
    explanation_tr: Mapped[str] = mapped_column(Text)
    hint_template_tr: Mapped[str | None] = mapped_column(Text)
    l1_related: Mapped[bool] = mapped_column(server_default="false")
    examples: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    version: Mapped[int] = mapped_column(server_default="1")
    active: Mapped[bool] = mapped_column(server_default="true")


class FixedTest(Base):
    """Seviye ölçen sabit test (H3): sürümlü, onaylı, iki paralel form.

    Ön mü son mu olduğu kişiye bağlıdır: yarısı A ile başlar, yarısı B ile. Hatırlama testi
    (H1) burada değildir; kişiye özel kurulur (`app/assessment/retention.py`).
    """

    __tablename__ = "fixed_tests"
    __table_args__ = (
        CheckConstraint("purpose = 'placement'", name="purpose"),
        CheckConstraint("form IN ('A','B')", name="form"),
        Index(None, "purpose", "form", "version", unique=True),
        {"schema": CONTENT},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(String(16))
    form: Mapped[str] = mapped_column(String(1), server_default="A")
    version: Mapped[int]
    questions: Mapped[list[Any]] = mapped_column(JSONB)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_at: Mapped[datetime | None]
