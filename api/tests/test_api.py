"""HTTP uç noktaları: giriş, onam, hedef, geri bildirim, olaylar (test veritabanı, sahte LLM)."""

import os
import uuid
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.deps import get_db, get_email_sender, get_llm_client
from app.feedback.llm_schema import WritingFeedback
from app.main import app
from tests.conftest import _libpq_url
from tests.fakes import FakeClient


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_login_link(self, email: str, url: str) -> None:
        self.sent.append((email, url))

    def token_for(self, email: str) -> str:
        url = next(u for e, u in reversed(self.sent) if e.lower() == email.lower())
        return parse_qs(urlparse(url).query)["token"][0]


FEEDBACK = WritingFeedback(
    is_correct=False,
    errors=[{"code": "ARTICLE", "start": 10, "end": 10}],  # type: ignore[list-item]
    hint_tr="Meslekten önce küçük bir kelime eksik.",
    correction="I work as a teacher.",
)


@pytest.fixture(scope="module")
def engine(migrated_db: Config) -> Iterator[object]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()


@pytest.fixture
def client(engine: object, sender: FakeSender) -> Iterator[TestClient]:
    factory = sessionmaker(engine, expire_on_commit=False)  # type: ignore[call-overload]

    def test_db() -> Iterator[Session]:
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_email_sender] = lambda: sender
    app.dependency_overrides[get_llm_client] = lambda: FakeClient(FEEDBACK)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _email() -> str:
    return f"{uuid.uuid4().hex[:12]}@example.com"


def _invite(engine: object) -> str:
    code = uuid.uuid4().hex[:8].upper()
    with Session(engine) as s:  # type: ignore[call-overload]
        s.execute(text("INSERT INTO learning.invites (code) VALUES (:c)"), {"c": code})
        s.commit()
    return code


def _login(client: TestClient, sender: FakeSender, engine: object, email: str | None = None) -> str:
    email = email or _email()
    r = client.post("/api/auth/request", json={"email": email, "invite_code": _invite(engine)})
    assert r.status_code == 202
    r = client.post("/api/auth/verify", json={"token": sender.token_for(email)})
    assert r.status_code == 200
    return email


def _consent(client: TestClient) -> None:
    r = client.post(
        "/api/onboarding/consent",
        json={"consent_version": settings.consent_version, "is_adult_confirmed": True},
    )
    assert r.status_code == 200


# --- Giriş -------------------------------------------------------------------


def test_unknown_email_without_invite_gets_no_link(client: TestClient, sender: FakeSender) -> None:
    r = client.post("/api/auth/request", json={"email": _email()})
    assert r.status_code == 202 and sender.sent == []


def test_invalid_invite_is_rejected(client: TestClient) -> None:
    r = client.post("/api/auth/request", json={"email": _email(), "invite_code": "NOPE"})
    assert r.status_code == 400


def test_invite_signup_logs_in_and_link_works_once(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    email, code = _email(), _invite(engine)
    client.post("/api/auth/request", json={"email": email, "invite_code": code})
    token = sender.token_for(email)
    assert sender.sent[-1][1].startswith(f"{settings.app_origin}/auth/verify?token=")

    r = client.post("/api/auth/verify", json={"token": token})
    assert r.status_code == 200 and r.json()["consent_done"] is False
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").status_code == 200

    assert client.post("/api/auth/verify", json={"token": token}).status_code == 400
    # Davet harcandı: başka bir e-posta onu kullanamaz.
    r = client.post("/api/auth/request", json={"email": _email(), "invite_code": code})
    assert r.status_code == 400


def test_returning_user_needs_no_invite(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    email = _login(client, sender, engine)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    client.post("/api/auth/request", json={"email": email.upper()})  # büyük/küçük harf fark etmez
    r = client.post("/api/auth/verify", json={"token": sender.token_for(email.upper())})
    assert r.status_code == 200


def test_expired_link_is_rejected(client: TestClient, sender: FakeSender, engine: object) -> None:
    email = _email()
    client.post("/api/auth/request", json={"email": email, "invite_code": _invite(engine)})
    with Session(engine) as s:  # type: ignore[call-overload]
        s.execute(
            text(
                "UPDATE learning.login_tokens SET expires_at = now() - interval '1 minute' "
                "WHERE email = :e"
            ),
            {"e": email},
        )
        s.commit()
    r = client.post("/api/auth/verify", json={"token": sender.token_for(email)})
    assert r.status_code == 400


def test_login_requests_are_rate_limited(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    email = _login(client, sender, engine)
    sent_before = len(sender.sent)
    for _ in range(settings.login_requests_per_hour + 2):
        assert client.post("/api/auth/request", json={"email": email}).status_code == 202
    # Saatlik sınır: ilk giriş isteği de sayılır.
    assert len(sender.sent) - sent_before == settings.login_requests_per_hour - 1


# --- Onam ve hedef -------------------------------------------------------------


def test_learning_endpoints_require_consent(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    _login(client, sender, engine)
    goals = {"goal": "travel", "daily_minutes": 15, "weak_skills": ["listening"], "interests": []}
    assert client.post("/api/onboarding/goals", json=goals).status_code == 403

    stale = {"consent_version": "old", "is_adult_confirmed": True}
    assert client.post("/api/onboarding/consent", json=stale).status_code == 409
    _consent(client)

    goals["interests"] = ["Football ", "food", "football"]
    r = client.post("/api/onboarding/goals", json=goals)
    assert r.status_code == 200
    assert r.json()["interests"] == ["food", "football"]
    assert r.json()["consent_done"] is True


# --- Geri bildirim -----------------------------------------------------------


@pytest.fixture(scope="module")
def item_id(migrated_db: Config) -> int:
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.error_tags (code, name_tr, explanation_tr) VALUES "
            "('ARTICLE', 'Artikel', 'Tekil sayılabilen isimden önce a/an gelir.'), "
            "('OTHER', 'Diğer', 'Başka bir hata.') ON CONFLICT DO NOTHING"
        )
        conn.execute(
            "INSERT INTO content.vocab_allowlist (lemma, cefr, source) "
            "SELECT w, 'A1', 'test' FROM unnest(ARRAY['i','work','as','a','teacher']) w "
            "ON CONFLICT DO NOTHING"
        )
        row = conn.execute(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr) "
            "VALUES ('test', 'chunk', 'work as', 'olarak çalışmak', 'A1') RETURNING id"
        ).fetchone()
    assert row is not None
    return int(row[0])


def test_feedback_and_rewrite(
    client: TestClient, sender: FakeSender, engine: object, item_id: int
) -> None:
    _login(client, sender, engine)
    _consent(client)
    body = {
        "task": "Write about your job.",
        "target_item_ids": [item_id],
        "text": "I work as teacher.",
    }
    r = client.post("/api/feedback", json=body)
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["status"] == "shown" and view["errors"][0]["code"] == "ARTICLE"
    assert "correction" not in view

    r = client.post(
        f"/api/feedback/{view['feedback_id']}/rewrite", json={"text": "I work as a teacher."}
    )
    assert r.json() == {"correction": "I work as a teacher."}

    # Başka bir kullanıcı bu geri bildirimi göremez.
    client.cookies.clear()
    _login(client, sender, engine)
    _consent(client)
    r = client.post(f"/api/feedback/{view['feedback_id']}/rewrite", json={"text": "x"})
    assert r.status_code == 404


# --- İstemci olayları --------------------------------------------------------


def test_client_events(client: TestClient, sender: FakeSender, engine: object) -> None:
    _login(client, sender, engine)
    _consent(client)
    ok = client.post("/api/events", json={"type": "nps_submitted", "payload": {"score": 9}})
    assert ok.status_code == 201

    bad_payload = client.post(
        "/api/events", json={"type": "nps_submitted", "payload": {"score": 11}}
    )
    assert bad_payload.status_code == 422
    # Derecelendirilmiş olaylar istemciden yazılamaz.
    rated = client.post("/api/events", json={"type": "answer_submitted", "payload": {}})
    assert rated.status_code == 422
    foreign = client.post("/api/events", json={"type": "activity_shown", "activity_id": 999999})
    assert foreign.status_code == 404
