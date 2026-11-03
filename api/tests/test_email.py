"""SMTP gönderici: gerçek sunucuya gitmeden (smtplib.SMTP yerine sahte sınıf)."""

import smtplib
from email.message import EmailMessage
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.auth import email as email_module
from app.auth.email import (
    ConsoleEmailSender,
    EmailSendError,
    SmtpEmailSender,
    login_message,
    sender_from_settings,
)
from app.config import settings
from app.deps import get_email_sender
from app.main import app
from tests.test_api import _email, _invite, client, engine, sender  # noqa: F401 - fixture'lar

URL = "http://localhost:3000/auth/verify?token=abc"


class FakeSMTP:
    instances: list[FakeSMTP] = []
    fail = False

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.calls.append("quit")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login:{user}")

    def send_message(self, message: EmailMessage) -> None:
        if FakeSMTP.fail:
            raise smtplib.SMTPRecipientsRefused({})
        self.sent.append(message)


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSMTP.instances, FakeSMTP.fail = [], False
    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)


def test_message_is_turkish_with_text_and_html() -> None:
    message = login_message("ali@example.com", URL)
    assert message["Subject"] == "Giriş bağlantın" and message["To"] == "ali@example.com"
    text = message.get_body(("plain",)).get_content()  # type: ignore[union-attr]
    html = message.get_body(("html",)).get_content()  # type: ignore[union-attr]
    assert URL in text and f'href="{URL}"' in html
    assert f"{settings.login_token_ttl_minutes} dakika" in text


def test_smtp_sender_uses_tls_and_login() -> None:
    SmtpEmailSender("smtp-relay.brevo.com", 587, "user", "secret").send_login_link(
        "ali@example.com", URL
    )
    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp-relay.brevo.com", 587)
    assert smtp.calls[:2] == ["starttls", "login:user"]
    assert len(smtp.sent) == 1


def test_smtp_failure_is_reported() -> None:
    FakeSMTP.fail = True
    with pytest.raises(EmailSendError):
        SmtpEmailSender("h", 587, None, None).send_login_link("ali@example.com", URL)


def test_sender_choice_follows_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)
    assert isinstance(sender_from_settings(), ConsoleEmailSender)
    monkeypatch.setattr(settings, "env", "production")
    with pytest.raises(RuntimeError):
        sender_from_settings()  # canlıda e-posta zorunlu
    monkeypatch.setattr(settings, "smtp_host", "smtp-relay.brevo.com")
    assert isinstance(sender_from_settings(), SmtpEmailSender)


class Broken:
    def send_login_link(self, email: str, url: str) -> None:
        raise EmailSendError


def test_failed_send_returns_503_and_stores_no_token(
    client: TestClient,  # noqa: F811 - test_api'deki fixture
    engine: Engine,  # noqa: F811
) -> None:
    app.dependency_overrides[get_email_sender] = lambda: Broken()
    email = _email()
    r = client.post("/api/auth/request", json={"email": email, "invite_code": _invite(engine)})
    assert r.status_code == 503
    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT count(*) FROM learning.login_tokens WHERE email = :e"), {"e": email}
        ).scalar_one()
    assert stored == 0  # istek geri alındı
