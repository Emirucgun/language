"""Bekleyen geri bildirim: "şimdilik atladık" → saatlik yeniden deneme → panelde hazır."""

import asyncio
import uuid

import pytest
from procrastinate.testing import InMemoryConnector
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import jobs
from app.events.service import record_event
from app.feedback.models import Feedback
from app.feedback.retry import MAX_ATTEMPTS, pending_writings, ready_for, retry_writing
from tests.fakes import FakeClient
from tests.test_feedback_flow import (  # noqa: F401 - fixture'lar
    LEXICON,
    TEXT,
    _feedback,
    _give,
    item_id,
    session,
    user,
)


@pytest.fixture(autouse=True)
def small_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    # Yeniden deneme sözlüğü veritabanından yükler; testte küçük sözlük yeter.
    monkeypatch.setattr("app.feedback.service.load_lexicon", lambda _db: LEXICON)


def _deferred_writing(session: Session, user: uuid.UUID, item_id: int) -> int:  # noqa: F811
    view = _give(session, user, item_id, FakeClient(None))
    assert view.status == "deferred"
    return view.writing_event_id


def test_deferred_writing_is_retried_and_becomes_ready(
    session: Session,  # noqa: F811
    user: uuid.UUID,  # noqa: F811
    item_id: int,  # noqa: F811
) -> None:
    writing_id = _deferred_writing(session, user, item_id)
    assert writing_id in pending_writings(session)

    client = FakeClient(_feedback())
    view = retry_writing(session, client, writing_id)
    assert view is not None and view.status == "shown"
    # Görev yeniden kuruldu: serbest pratik şablonu, aynı öğe.
    assert 'using "work as"' in client.requests[0].task
    assert writing_id not in pending_writings(session)

    ready = ready_for(session, user)
    assert [r.learner_text for r in ready] == [TEXT]
    assert ready[0].view.errors[0].code == "ARTICLE"

    record_event(
        session,
        user_id=user,
        type="feedback_shown",
        payload={"feedback_id": ready[0].view.feedback_id},
    )
    assert ready_for(session, user) == []


def test_immediate_feedback_is_not_listed_as_ready(
    session: Session,  # noqa: F811
    user: uuid.UUID,  # noqa: F811
    item_id: int,  # noqa: F811
) -> None:
    assert _give(session, user, item_id, FakeClient(_feedback())).status == "shown"
    assert ready_for(session, user) == []


def test_attempts_are_capped(session: Session, user: uuid.UUID, item_id: int) -> None:  # noqa: F811
    writing_id = _deferred_writing(session, user, item_id)
    for _ in range(MAX_ATTEMPTS):
        retry_writing(session, FakeClient(None), writing_id)
    attempts = session.scalar(
        select(func.count()).select_from(Feedback).where(Feedback.writing_event_id == writing_id)
    )
    assert attempts == MAX_ATTEMPTS
    assert writing_id not in pending_writings(session)
    assert retry_writing(session, FakeClient(_feedback()), writing_id) is None


def test_old_writings_are_left_alone(session: Session, user: uuid.UUID, item_id: int) -> None:  # noqa: F811
    writing_id = _deferred_writing(session, user, item_id)
    # Olaylar uygulama rolüyle değiştirilemez; zamanı geriye almak için yeni, eski tarihli
    # bir yazı eklenir.
    old_id = session.execute(
        text(
            "INSERT INTO learning.events "
            "(user_id, type, occurred_at, recorded_at, item_id, payload) "
            "VALUES (:u, 'writing_submitted', now() - interval '10 days', "
            'now() - interval \'10 days\', :i, \'{"text": "x", "attempt": 1}\') RETURNING id'
        ),
        {"u": user, "i": item_id},
    ).scalar_one()
    session.execute(
        text(
            "INSERT INTO learning.feedbacks (writing_event_id, status, validator_result) "
            "VALUES (:w, 'deferred', '{}')"
        ),
        {"w": old_id},
    )
    pending = pending_writings(session)
    assert writing_id in pending and old_id not in pending


def test_scheduler_queues_each_writing_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs, "_pending_feedback", lambda: [11, 12])
    connector = InMemoryConnector()
    with jobs.app.replace_connector(connector):
        assert asyncio.run(jobs.schedule_feedback_retries(timestamp=0)) == 2
        assert asyncio.run(jobs.schedule_feedback_retries(timestamp=3600)) == 0
    queued = sorted(
        j["args"]["writing_event_id"]
        for j in connector.jobs.values()
        if j["task_name"] == "retry_feedback"
    )
    assert queued == [11, 12]
