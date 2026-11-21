"""Ek çalışma: tür öğrenciden, öğeler kural katmanından; öneri ve seçim ayrı kaydedilir."""

import os
import uuid
from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.events.models import Event
from app.llm.models import LlmCall
from app.scheduler.service import update_item_states
from app.sessions import extra, service
from app.sessions.models import Activity, ActivityContent
from app.sessions.schemas import AnswerRequest
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401
from tests.test_session import LEXICON, SessionFake, item_ids  # noqa: F401


@pytest.fixture(autouse=True)
def small_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.sessions.generation.load_lexicon", lambda _db: LEXICON)


@pytest.fixture
def db(migrated_db: Config, item_ids: list[int]) -> Iterator[Session]:
    eng = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(eng) as s:
        yield s
        s.rollback()
    eng.dispose()


def _user(db: Session) -> User:
    user_id = db.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes) "
            "VALUES (:e, 'work', 15) RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@example.com"},
    ).scalar_one()
    return db.get_one(User, user_id)


def _practised(db: Session, item_ids: list[int]) -> User:
    """İlk iki öğeyi görmüş kullanıcı; ikincisinde zorlanmış (Again)."""
    user = _user(db)
    for item, rating in ((item_ids[0], 3), (item_ids[1], 1), (item_ids[1], 1)):
        db.execute(
            text(
                "INSERT INTO learning.events (user_id, type, occurred_at, item_id, rating) "
                "VALUES (:u, 'answer_submitted', now(), :i, :r)"
            ),
            {"u": user.id, "i": item, "r": rating},
        )
    update_item_states(db, user.id)
    return user


def test_nothing_to_practise_before_any_item_is_seen(db: Session) -> None:
    with pytest.raises(extra.NothingToPractise):
        extra.generate_extra(db, SessionFake(), _user(db), "recall")


def test_recall_extra_uses_seen_items_and_records_the_choice(
    db: Session, item_ids: list[int]
) -> None:
    user, fake = _practised(db, item_ids), SessionFake()
    ids = extra.generate_extra(db, fake, user, "recall")

    rows = db.execute(
        select(Activity, ActivityContent)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(Activity.id.in_(ids))
    ).all()
    assert {c.kind for _, c in rows} == {"recall"}
    assert {a.origin for a, _ in rows} == {"extra"} and all(a.session_id is None for a, _ in rows)
    # Yalnızca görülmüş öğeler; vadesi gelen (Again) dahil.
    assert {c.item_ids[0] for _, c in rows} == {item_ids[0], item_ids[1]}
    assert "new_item for: none" in fake.tasks[0]

    choice = db.scalar(
        select(Event.payload).where(Event.user_id == user.id, Event.type == "extra_activity_chosen")
    )
    assert choice is not None and choice["chosen_kind"] == "recall"
    recommended = choice["recommended_kind"] == "recall"
    assert all(a.recommended == recommended for a, _ in rows)


def test_extra_calls_are_logged_under_their_own_purpose(db: Session, item_ids: list[int]) -> None:
    user = _practised(db, item_ids)
    extra.generate_extra(db, SessionFake(), user, "recall")
    purposes = db.scalars(select(LlmCall.purpose).where(LlmCall.user_id == user.id)).all()
    assert purposes and set(purposes) == {"extra"}


def test_reading_extra_and_server_grading(db: Session, item_ids: list[int]) -> None:
    user = _practised(db, item_ids)
    [reading_id] = extra.generate_extra(db, SessionFake(), user, "reading")
    view = service.activity_view(db, *service.owned_activity(db, user.id, reading_id))
    assert view.kind == "reading" and len(view.questions) == 2
    result = service.answer(
        db, user.id, reading_id, AnswerRequest(question_id="q0", answer="Istanbul")
    )
    assert result.correct


def test_recommendation_follows_the_gap_between_plan_and_time(
    db: Session,
    item_ids: list[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user(db)
    assert extra.recommend(db, user) == "recall"  # veri yokken kelime ağırlığı en yüksek

    class OnlyVocabulary:
        minutes_by_skill = {"vocabulary": 12.0}

    monkeypatch.setattr(extra, "compute", lambda *_: OnlyVocabulary())
    assert extra.recommend(db, user) in ("reading", "writing")  # kelimeye yeterince zaman ayrıldı


def test_extra_endpoint_needs_seen_items(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    _login(client, sender, engine)
    _consent(client)
    assert client.get("/api/practice/recommendation").json()["recommended"] == "recall"
    r = client.post("/api/practice/extra", json={"kind": "recall"})
    assert r.status_code == 409 and "bugünün oturumunu" in r.json()["detail"]
