"""Geri bildirim akışı uçtan uca: sahte LLM → gerçek doğrulayıcı → test veritabanı."""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.events.models import Event
from app.feedback.llm_schema import WritingFeedback
from app.feedback.models import ErrorMark, Feedback
from app.feedback.service import give_feedback, submit_rewrite
from app.llm.models import LlmCall
from app.scheduler.models import ItemState
from app.validator.core import Lexicon
from tests.conftest import _libpq_url
from tests.fakes import FakeClient

A1_WORDS = "i she he is a an the work works as teacher my city very big"
LEXICON = Lexicon(frozenset(A1_WORDS.split()))
TASK = "Write a sentence about your job."
TEXT = "I work as teacher."


@pytest.fixture(scope="module")
def item_id(migrated_db: Config) -> int:
    # İçerik sahip rolüyle eklenir ve commit edilir; uygulama rolü yalnızca okur.
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.error_tags (code, name_tr, explanation_tr) VALUES "
            "('ARTICLE', 'Artikel', 'Tekil sayılabilen isimden önce a/an gelir.'), "
            "('BE_VERB', 'Be fiili', 'İsim cümlelerinde am/is/are gerekir.'), "
            "('OTHER', 'Diğer', 'Başka bir hata.') ON CONFLICT DO NOTHING"
        )
        row = conn.execute(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr) "
            "VALUES ('test', 'chunk', 'work as', 'olarak çalışmak', 'A1') RETURNING id"
        ).fetchone()
    assert row is not None
    return int(row[0])


@pytest.fixture
def session(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


@pytest.fixture
def user(session: Session) -> uuid.UUID:
    return session.execute(
        text("INSERT INTO learning.users (email, goal) VALUES (:e, 'work') RETURNING id"),
        {"e": f"{uuid.uuid4()}@test.example"},
    ).scalar_one()


def _feedback(**kwargs: object) -> WritingFeedback:
    base: dict[str, object] = {
        "is_correct": False,
        "errors": [{"code": "ARTICLE", "start": 10, "end": 10}],
        "hint_tr": "Meslekten önce küçük bir kelime eksik.",
        "correction": "I work as a teacher.",
    }
    return WritingFeedback.model_validate(base | kwargs)


def _give(session: Session, user: uuid.UUID, item_id: int, client: FakeClient, **kw: object):  # type: ignore[no-untyped-def]
    return give_feedback(
        session,
        client,
        user_id=user,
        task=TASK,
        target_item_ids=[item_id],
        learner_text=str(kw.get("learner_text", TEXT)),
        lexicon=LEXICON,
    )


def _event_types(session: Session, user: uuid.UUID) -> list[str]:
    return list(session.scalars(select(Event.type).where(Event.user_id == user).order_by(Event.id)))


def test_valid_feedback_is_shown_and_updates_the_learner_model(
    session: Session, user: uuid.UUID, item_id: int
) -> None:
    errors = [
        {"code": "ARTICLE", "start": 10, "end": 10},
        {"code": "OTHER", "start": 0, "end": 1},
        {"code": "BE_VERB", "start": 2, "end": 2},
    ]
    view = _give(session, user, item_id, FakeClient(_feedback(errors=errors)))

    assert view.status == "shown" and view.is_correct is False
    assert [e.code for e in view.errors] == ["ARTICLE", "OTHER"]  # en fazla 2
    assert view.errors[0].explanation_tr.startswith("Tekil")  # açıklama katalogdan
    assert not hasattr(view, "correction")  # doğru cümle henüz gösterilmez

    marks = session.scalars(select(ErrorMark).order_by(ErrorMark.id)).all()[-3:]
    assert [m.shown for m in marks] == [True, True, False]
    assert _event_types(session, user) == ["writing_submitted", "writing_assessed"]
    state = session.get(ItemState, (user, item_id))
    assert state is not None and state.reps == 1

    correction = submit_rewrite(session, user_id=user, feedback_id=view.feedback_id or 0, text=TEXT)
    assert correction == "I work as a teacher."
    assert _event_types(session, user)[-1] == "rewrite_submitted"


def test_correct_sentence_is_rated_good(session: Session, user: uuid.UUID, item_id: int) -> None:
    correct = _feedback(is_correct=True, errors=[], hint_tr=None, correction=None)
    view = _give(session, user, item_id, FakeClient(correct), learner_text="I work as a teacher.")
    assert view.status == "shown" and view.is_correct and view.errors == ()
    rating = session.scalar(
        select(Event.rating).where(Event.user_id == user, Event.type == "writing_assessed")
    )
    assert rating == 3


def test_leaking_hint_never_reaches_the_learner(
    session: Session, user: uuid.UUID, item_id: int
) -> None:
    leaking = _feedback(hint_tr="Doğrusu: I work as a teacher.")
    view = _give(session, user, item_id, FakeClient(leaking))

    assert view.status == "deferred" and view.hint_tr is None
    feedback = session.get_one(Feedback, view.feedback_id)
    assert feedback.status == "rejected"
    assert feedback.hint_tr is None and feedback.correction is None
    assert feedback.validator_result["issues"][0]["code"] == "answer_leak"
    # Reddedilen geri bildirim öğrenci modelini etkilemez.
    assert _event_types(session, user) == ["writing_submitted"]
    assert session.get(ItemState, (user, item_id)) is None


def test_llm_failure_defers(session: Session, user: uuid.UUID, item_id: int) -> None:
    view = _give(session, user, item_id, FakeClient(None))
    assert view.status == "deferred"
    assert session.get_one(Feedback, view.feedback_id).status == "deferred"


def test_daily_limit_defers_without_calling_the_model(
    session: Session, user: uuid.UUID, item_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "llm_daily_call_limit_per_user", 0)
    client = FakeClient(_feedback())
    view = _give(session, user, item_id, client)
    assert view.status == "deferred" and view.feedback_id is None
    assert client.requests == []
    # Öğrencinin metni kaybolmaz: olay kaydında, sonra işlenmek üzere.
    assert _event_types(session, user) == ["writing_submitted"]


def test_same_day_calls_share_one_frozen_snapshot(
    session: Session, user: uuid.UUID, item_id: int
) -> None:
    client = FakeClient(_feedback())
    _give(session, user, item_id, client)
    _give(session, user, item_id, client)
    snapshot_ids = session.scalars(
        select(func.distinct(LlmCall.snapshot_id)).where(LlmCall.user_id == user)
    ).all()
    assert len(snapshot_ids) == 1
    # Önek bayt bayt aynı: önbellek tutar.
    first, second = client.requests
    assert first.static_block == second.static_block
    assert first.snapshot_block == second.snapshot_block
    assert "Recent errors on these items: ARTICLE" in second.task


def test_rewrite_belongs_to_its_owner(session: Session, user: uuid.UUID, item_id: int) -> None:
    view = _give(session, user, item_id, FakeClient(_feedback()))
    stranger = session.execute(
        text("INSERT INTO learning.users (email) VALUES (:e) RETURNING id"),
        {"e": f"{uuid.uuid4()}@test.example"},
    ).scalar_one()
    with pytest.raises(PermissionError):
        submit_rewrite(session, user_id=stranger, feedback_id=view.feedback_id or 0, text=TEXT)
