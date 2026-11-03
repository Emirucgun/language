"""Kullanıcı ve giriş tabloları. Kişisel veri yalnızca `users.email` ve `users.display_name`."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, SmallInteger, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db import LEARNING, Base, created_at_column


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": LEARNING}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    # Silme talebinde boşaltılır; bu yüzden nullable.
    email: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(80))
    goal: Mapped[str | None] = mapped_column(String(32))
    daily_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    interests: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    timezone: Mapped[str] = mapped_column(String(64), server_default="Europe/Istanbul")
    is_adult_confirmed: Mapped[bool] = mapped_column(server_default="false")
    consent_version: Mapped[str | None] = mapped_column(String(16))
    consent_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_column()
    deleted_at: Mapped[datetime | None]


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = {"schema": LEARNING}

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(f"{LEARNING}.users.id"))
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_column()


class LoginToken(Base):
    """Magic link token'ı; yalnızca SHA-256 özeti saklanır."""

    __tablename__ = "login_tokens"
    __table_args__ = {"schema": LEARNING}

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT, index=True)
    # Yeni kullanıcıda davet, bağlantıya tıklanınca harcanır (yanlış e-posta daveti yakmaz).
    invite_code: Mapped[str | None] = mapped_column(ForeignKey(f"{LEARNING}.invites.code"))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_column()


class AuthSession(Base):
    """Sunucu tarafı oturum; çerezdeki değerin yalnızca özeti saklanır."""

    __tablename__ = "auth_sessions"
    __table_args__ = {"schema": LEARNING}

    id_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{LEARNING}.users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created_at_column()
