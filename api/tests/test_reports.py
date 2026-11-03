"""Haftalık rapor ve yeniden planlama (test veritabanı, sahte planlayıcı)."""

import asyncio
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from procrastinate.testing import InMemoryConnector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app import jobs
from app.auth.models import User
from app.curriculum.service import ensure_curriculum
from app.reports.service import compute, week_start_for
from app.reports.weekly import weekly_review
from tests.conftest import _libpq_url
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401
from tests.test_curriculum import Planner
from tests.test_session import item_ids  # noqa: F401 - havuzda öğe olsun


@pytest.fixture
def db(migrated_db: Config, item_ids: list[int]) -> Iterator[Session]:  # noqa: F811
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.error_tags (code, name_tr, explanation_tr) VALUES "
            "('ARTICLE', 'Artikel', 'Tekil sayılabilen isimden önce a/an gelir.') "
            "ON CONFLICT DO NOTHING"
        )
    eng = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(eng) as s:
        yield s
        s.rollback()
    eng.dispose()


def _user(db: Session) -> User:
    user_id = db.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes, timezone) "
            "VALUES (:e, 'work', 15, 'Europe/Istanbul') RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@example.com"},
    ).scalar_one()
    return db.get_one(User, user_id)


def _event(
    db: Session,
    user: User,
    type_: str,
    *,
    item_id: int | None = None,
    rating: int | None = None,
    payload: str = "{}",
    at: datetime | None = None,
) -> int:
    return db.execute(
        text(
            "INSERT INTO learning.events (user_id, type, occurred_at, recorded_at, item_id, "
            "rating, payload) VALUES (:u, :t, :at, :at, :i, :r, CAST(:p AS jsonb)) RETURNING id"
        ),
        {
            "u": user.id,
            "t": type_,
            "at": at or datetime.now(UTC),
            "i": item_id,
            "r": rating,
            "p": payload,
        },
    ).scalar_one()


def _busy_week(db: Session, user: User, item_ids: list[int]) -> None:  # noqa: F811
    """Zorlanan bir hafta: 6 cevabın 2'si doğru, bir yazma hatası, bir "anlamadım"."""
    for n, rating in enumerate([3, 1, 1, 3, 1, 1]):
        _event(db, user, "answer_submitted", item_id=item_ids[n % 2], rating=rating)
    writing = _event(
        db, user, "writing_submitted", payload='{"text": "I am teacher", "attempt": 1}'
    )
    feedback = db.execute(
        text(
            "INSERT INTO learning.feedbacks (writing_event_id, status, validator_result) "
            "VALUES (:w, 'shown', '{}') RETURNING id"
        ),
        {"w": writing},
    ).scalar_one()
    db.execute(
        text(
            "INSERT INTO learning.error_marks (feedback_id, tag_code, span_start, span_end, shown) "
            "VALUES (:f, 'ARTICLE', 5, 5, true)"
        ),
        {"f": feedback},
    )
    _event(
        db, user, "feedback_reaction", payload=f'{{"feedback_id": {feedback}, "understood": false}}'
    )
    _event(db, user, "session_completed", payload='{"session_id": 1}')


def test_metrics_come_from_this_weeks_events_only(db: Session, item_ids: list[int]) -> None:  # noqa: F811
    user = _user(db)
    _busy_week(db, user, item_ids)
    _event(
        db,
        user,
        "answer_submitted",
        item_id=item_ids[2],
        rating=3,
        at=datetime.now(UTC) - timedelta(days=30),
    )

    m = compute(db, user, week_start_for(user, datetime.now(UTC)))
    assert (m.answers, m.success_rate, m.new_items) == (6, 0.33, 2)
    assert m.sessions_completed == 1 and m.active_days == 1
    assert m.understood_rate == 0.0 and m.minutes_by_skill["writing"] == 1.5
    assert m.top_error is not None and m.top_error.code == "ARTICLE"
    assert m.top_error.explanation_tr.startswith("Tekil")
    assert m.pace == "slow"


def test_weekly_review_replans_slower_without_seen_items(db: Session, item_ids: list[int]) -> None:  # noqa: F811
    user, planner = _user(db), Planner()
    ensure_curriculum(db, planner, user)
    _busy_week(db, user, item_ids)
    report = weekly_review(db, planner, user, week_start_for(user, datetime.now(UTC)))

    replan = planner.tasks[-1]
    assert "WEEKLY REPLAN" in replan and "pace decided by the app: slow" in replan
    assert "max new items per week): 14" in replan  # 18 * 0.75
    assert f"\n{item_ids[0]} |" not in replan  # görülen öğe havuzda yok
    assert report.metrics["plan_changed"] is True and report.metrics["curriculum_version"] == 2

    # Aynı hafta tekrar: yeni çağrı ya da rapor yok.
    calls = len(planner.tasks)
    assert weekly_review(db, planner, user, report.week_start).id == report.id
    assert len(planner.tasks) == calls


def test_inactive_week_writes_a_report_but_spends_nothing(db: Session) -> None:
    user, planner = _user(db), Planner()
    report = weekly_review(db, planner, user, week_start_for(user, datetime.now(UTC)))
    assert report.metrics["plan_changed"] is False and planner.tasks == []
    assert report.metrics["active_days"] == 0


def test_review_job_is_queued_once_per_user_and_week(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    monkeypatch.setattr(jobs, "_due_reviews", lambda: [(user_id, datetime(2026, 11, 2).date())])
    connector = InMemoryConnector()
    with jobs.app.replace_connector(connector):
        assert asyncio.run(jobs.schedule_weekly_reviews(timestamp=0)) == 1
        assert asyncio.run(jobs.schedule_weekly_reviews(timestamp=3600)) == 0
    queued = [j for j in connector.jobs.values() if j["task_name"] == "weekly_review"]
    assert [j["args"] for j in queued] == [{"user_id": str(user_id), "week_start": "2026-11-02"}]


def test_latest_report_endpoint(client: TestClient, sender: FakeSender, engine: object) -> None:  # noqa: F811
    _login(client, sender, engine)
    _consent(client)
    assert client.get("/api/reports/latest").status_code == 404

    user_id = uuid.UUID(client.get("/api/auth/me").json()["id"])
    with Session(engine) as s:  # type: ignore[call-overload]
        user = s.get_one(User, user_id)
        weekly_review(s, Planner(), user, week_start_for(user, datetime.now(UTC)))
        s.commit()
    body = client.get("/api/reports/latest").json()
    assert body["metrics"]["active_days"] >= 0 and "success_rate" in body["metrics"]
