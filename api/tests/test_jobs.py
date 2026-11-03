"""Gece ön üretimi: kim seçilir, iş kuyruğa nasıl girer, iş oturumu nasıl üretir."""

import asyncio
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from alembic.config import Config
from procrastinate.testing import InMemoryConnector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import jobs
from app.sessions.scheduling import users_needing_session
from tests.test_session import LEXICON, SessionFake, item_ids  # noqa: F401 - fixture


def _tz_with_local_hour(hour: int) -> str:
    """Şu an yerel saatin `hour` olduğu sabit ofsetli bir saat dilimi (Etc/GMT işareti terstir)."""
    utc_hour = datetime.now(UTC).hour
    for offset in range(-12, 15):
        if (utc_hour + offset) % 24 == hour:
            return f"Etc/GMT{-offset:+d}" if offset else "UTC"
    raise AssertionError("uygun ofset yok")


@pytest.fixture
def db(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


def _user(
    db: Session,
    *,
    tz: str,
    consent: bool = True,
    goal: str | None = "work",
    created_days_ago: int = 0,
) -> uuid.UUID:
    return db.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes, timezone, consent_at, "
            "is_adult_confirmed, created_at) VALUES (:e, :g, 15, :tz, "
            "CASE WHEN :c THEN now() END, :c, now() - make_interval(days => :d)) RETURNING id"
        ),
        {
            "e": f"{uuid.uuid4()}@example.com",
            "g": goal,
            "tz": tz,
            "c": consent,
            "d": created_days_ago,
        },
    ).scalar_one()


def test_selection_rules(db: Session) -> None:
    after_three, before_three = _tz_with_local_hour(5), _tz_with_local_hour(1)
    due = _user(db, tz=after_three)
    too_early = _user(db, tz=before_three)
    no_consent = _user(db, tz=after_three, consent=False)
    no_goal = _user(db, tz=after_three, goal=None)
    inactive = _user(db, tz=after_three, created_days_ago=30)
    returning = _user(db, tz=after_three, created_days_ago=30)
    db.execute(
        text(
            "INSERT INTO learning.events (user_id, type, occurred_at) "
            "VALUES (:u, 'report_viewed', now())"
        ),
        {"u": returning},
    )
    ready = _user(db, tz=after_three)
    db.execute(
        text(
            "INSERT INTO learning.study_sessions (user_id, local_date, status) "
            "VALUES (:u, (now() AT TIME ZONE :tz)::date, 'ready')"
        ),
        {"u": ready, "tz": after_three},
    )

    selected = {user_id for user_id, _ in users_needing_session(db)}
    assert {due, returning} <= selected
    assert selected.isdisjoint({too_early, no_consent, no_goal, inactive, ready})


def test_scheduler_queues_one_job_per_user_and_day(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, today = uuid.uuid4(), date(2026, 11, 9)
    monkeypatch.setattr(jobs, "_due", lambda: [(user_id, today)])
    connector = InMemoryConnector()
    with jobs.app.replace_connector(connector):
        assert asyncio.run(jobs.schedule_sessions(timestamp=0)) == 1
        # Bir sonraki tur (iş henüz çalışmadan) aynı işi tekrar kuyruğa koymaz.
        assert asyncio.run(jobs.schedule_sessions(timestamp=900)) == 0

    queued = [j for j in connector.jobs.values() if j["task_name"] == "generate_session"]
    assert len(queued) == 1
    assert queued[0]["args"] == {"user_id": str(user_id), "local_date": "2026-11-09"}


@pytest.mark.usefixtures("item_ids")  # oturumda öğe olsun diye (tests/test_session.py)
def test_generate_session_job_builds_and_commits(
    migrated_db: Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    monkeypatch.setattr(jobs, "SessionLocal", sessionmaker(engine, expire_on_commit=False))
    fake = SessionFake()
    monkeypatch.setattr(jobs, "get_llm_client", lambda: fake)
    monkeypatch.setattr("app.sessions.generation.load_lexicon", lambda _db: LEXICON)

    with Session(engine) as s:
        user_id = _user(s, tz="Europe/Istanbul")
        s.commit()

    assert jobs.generate_session(user_id=str(user_id), local_date="2026-11-12") == "ready"
    # Tekrar denenirse (ör. retry) yeni LLM çağrısı yapılmaz.
    assert jobs.generate_session(user_id=str(user_id), local_date="2026-11-12") == "ready"
    assert len(fake.tasks) == 1
    engine.dispose()
