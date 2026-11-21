"""İnceleme kuyruğu: rol, öncelik, kimlik gizliliği ve H4 için kaynak ayrımı."""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.events.service import record_event
from app.feedback.models import ErrorMark, Feedback
from app.reports.models import Review
from app.review import service
from app.sessions.models import Activity, ActivityContent
from app.sessions.schemas import Choice, Recall
from tests.conftest import _libpq_url
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401

RECALL = Recall(
    item_id=1,
    question=Choice(prompt="I ___ tea.", options=["like", "likes", "liking"], answer="like"),
    hint_tr="Çayı severim.",
)


@pytest.fixture
def db(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


@pytest.fixture(scope="module")
def tag(migrated_db: Config) -> str:
    """İçerik şeması uygulama rolüne kapalı: sahip rolüyle."""
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.error_tags (code, name_tr, explanation_tr) "
            "VALUES ('ARTICLE', 'Artikel', 'a/an') ON CONFLICT DO NOTHING"
        )
    return "ARTICLE"


def _user(db: Session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", timezone="UTC")
    db.add(user)
    db.flush()
    return user


def _content(db: Session, *, model: str | None = "llm") -> ActivityContent:
    content = ActivityContent(
        content_hash=os.urandom(32),
        kind="recall",
        item_ids=[],
        cefr_sub="A1.1",
        content=RECALL.model_dump(),
        model=model,
        validator_version="v1",
        validator_result={},
        status="approved",
        shareable=True,
    )
    db.add(content)
    db.flush()
    return content


def _activity(db: Session, user: User, content: ActivityContent) -> Activity:
    activity = Activity(user_id=user.id, content_id=content.id, origin="session", recommended=False)
    db.add(activity)
    db.flush()
    return activity


def _feedback(db: Session, user: User, learner_text: str = "I am work as teacher.") -> Feedback:
    event = record_event(
        db, user_id=user.id, type="writing_submitted", payload={"text": learner_text, "attempt": 1}
    )
    feedback = Feedback(
        writing_event_id=event.id,
        status="shown",
        hint_tr="Meslekten önce küçük bir kelime eksik.",
        correction="I work as a teacher.",
        validator_result={},
    )
    db.add(feedback)
    db.flush()
    return feedback


def _flag(db: Session, user: User, activity: Activity, reason: str = "Yanlış bilgi") -> None:
    record_event(
        db,
        user_id=user.id,
        type="activity_flagged",
        payload={"reason": reason},
        activity_id=activity.id,
    )


def _drain_flags(db: Session, reviewer: User) -> None:
    """Başka testlerin kalıcı bayrakları sonucu etkilemesin."""
    for target in service.pending_flags(db):
        service.submit(
            db,
            reviewer,
            target_type=target.target_type,
            target_id=target.target_id,
            verdict="correct",
            notes=None,
        )


def _submit(db: Session, reviewer: User, target: service.Target, verdict: str) -> Review:
    return service.submit(
        db,
        reviewer,
        target_type=target.target_type,
        target_id=target.target_id,
        verdict=verdict,  # type: ignore[arg-type]
        notes=None,
    )


def test_flagged_content_comes_before_any_sample(db: Session) -> None:
    learner, reviewer = _user(db), _user(db)
    _drain_flags(db, reviewer)
    _content(db)
    flagged = _content(db)
    _flag(db, learner, _activity(db, learner, flagged))

    target = service.next_target(db)

    assert target is not None
    assert (target.target_id, target.source, target.reason) == (flagged.id, "flag", "Yanlış bilgi")


def test_repeated_flags_are_one_entry_and_review_closes_them(db: Session) -> None:
    first, second, reviewer = _user(db), _user(db), _user(db)
    _drain_flags(db, reviewer)
    content = _content(db)
    _flag(db, first, _activity(db, first, content))
    _flag(db, second, _activity(db, second, content))

    assert [t.target_id for t in service.pending_flags(db)] == [content.id]
    _submit(db, reviewer, service.pending_flags(db)[0], "correct")
    assert service.pending_flags(db) == []


def test_source_is_decided_by_the_server(db: Session) -> None:
    """H4 oranını işaretli içerik şişirmesin."""
    learner, reviewer = _user(db), _user(db)
    _drain_flags(db, reviewer)
    flagged, plain = _content(db), _content(db)
    _flag(db, learner, _activity(db, learner, flagged))

    from_flag = _submit(
        db, reviewer, service.Target("activity_content", flagged.id, "sample"), "wrong_teaching"
    )
    from_sample = _submit(
        db, reviewer, service.Target("activity_content", plain.id, "flag"), "correct"
    )

    assert from_flag.source == "flag"
    assert from_sample.source == "sample"


def test_sample_skips_templates_and_reviewed_items(db: Session) -> None:
    reviewer = _user(db)
    _drain_flags(db, reviewer)
    template, reviewed = _content(db, model=None), _content(db)
    _submit(db, reviewer, service.Target("activity_content", reviewed.id, "sample"), "correct")

    picked = {service.next_target(db) for _ in range(20)}

    assert all(t is None or t.source == "sample" for t in picked)
    ids = {t.target_id for t in picked if t and t.target_type == "activity_content"}
    assert ids.isdisjoint({template.id, reviewed.id})


def test_same_sample_cannot_be_counted_twice(db: Session) -> None:
    reviewer = _user(db)
    target = service.Target("activity_content", _content(db).id, "sample")
    _submit(db, reviewer, target, "correct")
    with pytest.raises(service.AlreadyReviewed):
        _submit(db, reviewer, target, "unclear")


def test_wrong_teaching_retires_shared_content(db: Session) -> None:
    reviewer = _user(db)
    content = _content(db)
    _submit(
        db, reviewer, service.Target("activity_content", content.id, "sample"), "wrong_teaching"
    )
    assert content.status == "retired"

    other = _content(db)
    _submit(db, reviewer, service.Target("activity_content", other.id, "sample"), "off_level")
    assert other.status == "approved"


def test_unknown_target_is_rejected(db: Session) -> None:
    with pytest.raises(service.TargetNotFound):
        _submit(db, _user(db), service.Target("feedback", 2_000_000_000, "sample"), "correct")


def test_activity_view_shows_the_answer(db: Session) -> None:
    item = service.render(db, service.Target("activity_content", _content(db).id, "sample"))
    lines = {line.label: line.text for line in item.lines}
    assert item.title == "Tekrar sorusu" and item.level == "A1.1"
    assert lines["Doğru cevap"] == "like"
    assert lines["Şıklar"] == "like / likes / liking"


def test_dialogue_view_shows_the_conversation_not_raw_keys(db: Session) -> None:
    user = _user(db)
    content = ActivityContent(
        content_hash=os.urandom(32),
        kind="dialogue",
        item_ids=[],
        cefr_sub="A1.1",
        content={"scenario": "hotel", "item_ids": []},
        validator_version="v1",
        validator_result={},
        status="approved",
        shareable=False,
    )
    db.add(content)
    db.flush()
    activity = _activity(db, user, content)
    writing = record_event(
        db,
        user_id=user.id,
        type="writing_submitted",
        payload={"text": "Yes, I have a room.", "attempt": 1},
        activity_id=activity.id,
    )
    record_event(
        db,
        user_id=user.id,
        type="dialogue_replied",
        payload={
            "turn": 1,
            "writing_event_id": writing.id,
            "feedback_id": None,
            "partner_en": "Great, what is your name?",
            "partner_tr": "Harika, adınız ne?",
            "source": "llm",
            "done": False,
        },
        activity_id=activity.id,
    )

    item = service.render(db, service.Target("activity_content", content.id, "flag"))

    labels = [line.label for line in item.lines]
    texts = [line.text for line in item.lines]
    assert item.title == "Diyalog"
    assert "Küçük bir otele giriş yapıyorsun." in texts
    assert "Yes, I have a room." in texts and "Great, what is your name?" in texts
    assert "scenario" not in labels and "item_ids" not in labels


def test_feedback_view_has_the_text_but_no_identity(db: Session) -> None:
    user = _user(db)
    feedback = _feedback(db, user)
    item = service.render(db, service.Target("feedback", feedback.id, "sample"))

    dumped = item.model_dump_json()
    assert "I am work as teacher." in dumped
    assert "I work as a teacher." in dumped
    assert str(user.id) not in dumped
    assert str(user.email) not in dumped


def test_feedback_view_quotes_the_marked_words(db: Session, tag: str) -> None:
    feedback = _feedback(db, _user(db))
    db.add(ErrorMark(feedback_id=feedback.id, tag_code=tag, span_start=2, span_end=4, shown=True))
    db.flush()
    item = service.render(db, service.Target("feedback", feedback.id, "sample"))
    assert any(line.label == "Gösterilen hata" and "“am”" in line.text for line in item.lines)


# --- HTTP ---------------------------------------------------------------------


def _make_reviewer(engine: object, email: str) -> None:
    with Session(engine) as s:  # type: ignore[call-overload]
        s.execute(
            text("UPDATE learning.users SET role = 'reviewer' WHERE email = :e"), {"e": email}
        )
        s.commit()


def test_learner_cannot_open_the_queue(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    _login(client, sender, engine)
    _consent(client)
    assert client.get("/api/review/next").status_code == 403
    r = client.post(
        "/api/review",
        json={"target_type": "feedback", "target_id": 1, "verdict": "correct"},
    )
    assert r.status_code == 403


def test_anonymous_cannot_open_the_queue(client: TestClient) -> None:
    assert client.get("/api/review/next").status_code == 401


def test_reviewer_needs_no_onboarding_and_sees_stats(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    email = _login(client, sender, engine)
    _make_reviewer(engine, email)

    r = client.get("/api/review/next")

    assert r.status_code == 200, r.text
    assert set(r.json()["stats"]) == {"sample_reviewed", "sample_wrong_teaching", "flags_pending"}
    assert client.get("/api/auth/me").json()["role"] == "reviewer"


def test_invalid_verdict_is_rejected(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    email = _login(client, sender, engine)
    _make_reviewer(engine, email)
    r = client.post(
        "/api/review", json={"target_type": "feedback", "target_id": 1, "verdict": "maybe"}
    )
    assert r.status_code == 422


# --- Bayrak hedefi (EK-6) -----------------------------------------------------


def test_flag_needs_a_target(client: TestClient, sender: FakeSender, engine: object) -> None:
    _login(client, sender, engine)
    _consent(client)
    r = client.post("/api/events", json={"type": "activity_flagged", "payload": {}})
    assert r.status_code == 422


def test_flag_on_someone_elses_feedback_is_refused(
    client: TestClient, sender: FakeSender, engine: object
) -> None:
    with Session(engine) as s:  # type: ignore[call-overload]
        feedback = _feedback(s, _user(s))
        s.commit()
        feedback_id = feedback.id
    _login(client, sender, engine)
    _consent(client)
    r = client.post(
        "/api/events",
        json={"type": "activity_flagged", "payload": {"feedback_id": feedback_id}},
    )
    assert r.status_code == 404
