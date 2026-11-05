"""FastAPI bağımlılıkları: veritabanı oturumu, LLM istemcisi, e-posta, giriş yapmış kullanıcı."""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.email import EmailSender, sender_from_settings
from app.auth.models import AuthSession, User
from app.config import settings
from app.db import SessionLocal
from app.llm.client import LLMClient
from app.llm.routing import routing_client
from app.llm.service import contains_email


def get_db() -> Iterator[Session]:
    """İstek başına bir transaction: başarıda commit, hatada geri alma."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def _secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value().strip() if value else None


@cache
def _router() -> LLMClient:
    return routing_client(_secret(settings.anthropic_api_key), _secret(settings.openai_api_key))


def get_llm_client() -> LLMClient:
    return _router()


def get_email_sender() -> EmailSender:
    return sender_from_settings()


def hash_secret(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def reject_personal_data(text: str) -> None:
    """E-posta içeren metin kaydedilmeden geri çevrilir; öğrencinin ekranında kalır."""
    if contains_email(text):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Metninde e-posta adresi var. Lütfen kişisel bilgi yazma; adresi silip tekrar gönder.",
        )


Db = Annotated[Session, Depends(get_db)]


def current_user(
    db: Db,
    session_cookie: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Giriş gerekli.")
    if not session_cookie:
        raise unauthorized
    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.id_hash == hash_secret(session_cookie),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
            User.deleted_at.is_(None),
        )
    ).first()
    if row is None:
        raise unauthorized
    return row[1]


CurrentUser = Annotated[User, Depends(current_user)]


def consented_user(user: CurrentUser) -> User:
    """Onam ve 18+ onayı olmadan öğrenme uç noktaları kapalı."""
    if user.consent_at is None or not user.is_adult_confirmed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Önce onam ekranı tamamlanmalı.")
    return user


ConsentedUser = Annotated[User, Depends(consented_user)]


def reviewer_user(user: CurrentUser) -> User:
    """İnceleyen öğrenci akışından geçmek zorunda değil: onam istenmez."""
    if user.role != "reviewer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu ekran inceleyenler içindir.")
    return user


ReviewerUser = Annotated[User, Depends(reviewer_user)]
