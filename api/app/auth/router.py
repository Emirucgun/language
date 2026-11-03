"""Magic link girişi (parolasız) ve oturum.

Akış: e-posta (+ yeni kullanıcıysa davet kodu) → tek kullanımlık bağlantı → bağlantı
doğrulanınca sunucu tarafı oturum ve httpOnly çerez. Token ve oturum değerlerinin
yalnızca SHA-256 özeti saklanır.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update

from app.auth.email import EmailSender
from app.auth.models import AuthSession, Invite, LoginToken, User
from app.config import settings
from app.deps import CurrentUser, Db, get_email_sender, hash_secret

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    invite_code: str | None = Field(default=None, max_length=32)


class VerifyRequest(BaseModel):
    token: str = Field(min_length=20, max_length=100)


class Me(BaseModel):
    id: str
    display_name: str | None
    goal: str | None
    daily_minutes: int | None
    interests: list[str]
    timezone: str
    consent_done: bool

    @classmethod
    def of(cls, user: User) -> Me:
        return cls(
            id=str(user.id),
            display_name=user.display_name,
            goal=user.goal,
            daily_minutes=user.daily_minutes,
            interests=list(user.interests),
            timezone=user.timezone,
            consent_done=user.consent_at is not None and user.is_adult_confirmed,
        )


def _invite_is_open(db: Db, code: str) -> bool:
    invite = db.get(Invite, code)
    return invite is not None and invite.used_at is None


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
def request_login(
    body: LoginRequest,
    db: Db,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> dict[str, bool]:
    """Yanıt, e-postanın kayıtlı olup olmadığını belli etmez.

    Yalnızca verilen davet kodu geçersizse 400 döner; bu, e-posta hakkında bilgi vermez.
    """
    if body.invite_code is not None and not _invite_is_open(db, body.invite_code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Davet kodu geçersiz.")

    user = db.scalar(select(User).where(User.email == body.email, User.deleted_at.is_(None)))
    invite_code = None if user else body.invite_code
    if user is None and invite_code is None:
        return {"ok": True}  # bilinmeyen e-posta, davet yok: sessizce bir şey yapma

    recent = db.scalar(
        select(func.count())
        .select_from(LoginToken)
        .where(
            LoginToken.email == body.email,
            LoginToken.created_at > datetime.now(UTC) - timedelta(hours=1),
        )
    )
    if (recent or 0) >= settings.login_requests_per_hour:
        return {"ok": True}

    token = secrets.token_urlsafe(32)
    db.add(
        LoginToken(
            token_hash=hash_secret(token),
            email=body.email,
            invite_code=invite_code,
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.login_token_ttl_minutes),
        )
    )
    db.flush()
    sender.send_login_link(
        body.email, f"{settings.app_origin}/auth/verify?{urlencode({'token': token})}"
    )
    return {"ok": True}


@router.post("/verify")
def verify_login(body: VerifyRequest, db: Db, response: Response) -> Me:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Bağlantı geçersiz ya da süresi dolmuş.")
    # Tek kullanımlık: koşullu güncelleme iki eşzamanlı tıklamadan yalnızca birini geçirir.
    login = db.scalars(
        update(LoginToken)
        .where(
            LoginToken.token_hash == hash_secret(body.token),
            LoginToken.used_at.is_(None),
            LoginToken.expires_at > datetime.now(UTC),
        )
        .values(used_at=datetime.now(UTC))
        .returning(LoginToken)
    ).first()
    if login is None:
        raise invalid

    user = db.scalar(select(User).where(User.email == login.email))
    if user is not None and user.deleted_at is not None:
        raise invalid
    if user is None:
        if login.invite_code is None:
            raise invalid
        invite = db.scalar(select(Invite).where(Invite.code == login.invite_code).with_for_update())
        if invite is None or invite.used_at is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Davet kodu kullanılmış.")
        user = User(email=login.email)
        db.add(user)
        db.flush()
        invite.used_by = user.id
        invite.used_at = datetime.now(UTC)

    session_value = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            id_hash=hash_secret(session_value),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
        )
    )
    response.set_cookie(
        settings.session_cookie_name,
        session_value,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return Me.of(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: Db,
    response: Response,
    session_cookie: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
) -> None:
    if session_cookie:
        db.execute(
            update(AuthSession)
            .where(AuthSession.id_hash == hash_secret(session_cookie))
            .values(revoked_at=datetime.now(UTC))
        )
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me")
def me(user: CurrentUser) -> Me:
    return Me.of(user)
