"""Yazılı diyalog: sabit açılış, tur başına tek çağrı, doğrulama, tur sınırları, yedek cümle."""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.dialogue import service
from app.dialogue.schemas import MAX_TURNS, MIN_TURNS, DialogueTurn, PartnerLine
from app.events.models import Event
from app.feedback.llm_schema import FoundError, WritingFeedback
from app.feedback.retry import pending_writings
from app.llm.client import LLMRequest, LLMResult
from app.llm.pricing import Usage
from app.validator.core import Lexicon
from tests.conftest import _libpq_url
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401
from tests.test_session import item_ids  # noqa: F401 - havuzda öğe olsun

LEXICON_WORDS = (
    "i am a an teacher work in school nice to meet you too what do where are is it the "
    "and like my your job yes no thank thanks bye see how about lunch today good"
)
LEXICON = Lexicon(frozenset(LEXICON_WORDS.split()))
CORRECT = WritingFeedback(is_correct=True, errors=[], hint_tr=None, correction=None)
ARTICLE = WritingFeedback(
    is_correct=False,
    errors=[FoundError(code="ARTICLE", quote="teacher", gap="before")],
    hint_tr="İşini söylerken bir şey eksik.",
    correction="I am a teacher.",
)


def _turn(en: str = "Nice to meet you too. Where do you work?", done: bool = False) -> DialogueTurn:
    return DialogueTurn(feedback=CORRECT, partner=PartnerLine(en=en, tr="Çeviri."), done=done)


class Partner:
    """Sırayla verilen cevapları döner; bitince sonuncuyu tekrarlar."""

    def __init__(self, *turns: DialogueTurn | None) -> None:
        self.turns = list(turns)
        self.tasks: list[str] = []

    def complete(self, request: LLMRequest) -> LLMResult:
        self.tasks.append(request.task)
        parsed = self.turns[min(len(self.tasks), len(self.turns)) - 1]
        return LLMResult(
            request.config.model, parsed, Usage(400, 150), "end_turn", 2000, None
        )


@pytest.fixture
def db(migrated_db: Config, item_ids: list[int]) -> Iterator[Session]:
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
            "INSERT INTO learning.users (email, goal, daily_minutes) "
            "VALUES (:e, 'work', 15) RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@example.com"},
    ).scalar_one()
    return db.get_one(User, user_id)


def _start(db: Session) -> service.Dialogue:
    user = _user(db)
    return service.load(db, user.id, service.start(db, user))


def _say(db: Session, partner: Partner, dialogue: service.Dialogue, text_: str) -> None:
    service.reply(db, partner, dialogue, text_, lexicon=LEXICON)


def test_start_is_fixed_and_free(db: Session) -> None:
    dialogue = _start(db)
    view = service.view(db, dialogue)
    assert dialogue.scenario.key == "new_colleague"  # hedef: iş
    assert view.opening.en.startswith("Hi! I'm Anna") and view.turns == [] and not view.done
    choice = db.scalar(
        select(Event.payload).where(
            Event.activity_id == dialogue.activity.id, Event.type == "extra_activity_chosen"
        )
    )
    assert choice is not None and choice["chosen_kind"] == "dialogue"
    # Sonraki diyalog başka senaryo.
    user = db.get_one(User, dialogue.activity.user_id)
    assert service.load(db, user.id, service.start(db, user)).scenario.key == "meeting_time"


def test_reply_shows_feedback_and_keeps_history_append_only(db: Session) -> None:
    dialogue, partner = _start(db), Partner(_turn(), _turn("What do you like about your job?"))
    _say(db, partner, dialogue, "I am teacher.")
    _say(db, partner, dialogue, "I work in a school.")

    first = partner.tasks[0]
    assert "You: Hi! I'm Anna" in first
    assert first.endswith("Learner: <learner_text>I am teacher.</learner_text>")
    assert partner.tasks[1].startswith(first.rsplit("\nLearner turn", 1)[0])  # önek aynı
    assert "Learner turn 2" in partner.tasks[1]

    view = service.view(db, dialogue)
    assert [t.learner for t in view.turns] == ["I am teacher.", "I work in a school."]
    assert view.turns[1].partner.en == "What do you like about your job?"
    assert view.turns[0].feedback is not None and view.turns[0].feedback.is_correct


def test_errors_are_marked_with_a_hint(db: Session) -> None:
    dialogue = _start(db)
    turn = DialogueTurn(feedback=ARTICLE, partner=_turn().partner, done=False)
    service.reply(db, Partner(turn), dialogue, "I am teacher.", lexicon=LEXICON)
    [shown] = service.view(db, dialogue).turns
    assert shown.feedback is not None and shown.feedback.hint_tr == ARTICLE.hint_tr
    assert [e.code for e in shown.feedback.errors] == ["ARTICLE"]


def test_turn_limits_are_enforced_by_rules(db: Session) -> None:
    dialogue, partner = _start(db), Partner(_turn(done=True))  # model hep bitirmek istiyor
    for n in range(1, MIN_TURNS):
        _say(db, partner, dialogue, "Yes.")
        assert not service.view(db, dialogue).done, n
    _say(db, partner, dialogue, "Yes.")
    assert service.view(db, dialogue).done
    with pytest.raises(service.DialogueFinished):
        _say(db, partner, dialogue, "Bye.")

    dialogue, partner = _start(db), Partner(_turn(done=False))  # model hiç bitirmiyor
    for _ in range(MAX_TURNS):
        _say(db, partner, dialogue, "Yes.")
    assert service.view(db, dialogue).done and "last learner turn" in partner.tasks[-1]


def test_bad_partner_line_is_retried_then_replaced(db: Session) -> None:
    dialogue = _start(db)
    off_level = _turn("Fantastic! Which department are you responsible for?")
    partner = Partner(off_level, off_level)
    _say(db, partner, dialogue, "I am a teacher.")
    assert len(partner.tasks) == 2
    [shown] = service.view(db, dialogue).turns
    assert shown.partner == service.FALLBACK_CONTINUE
    assert shown.feedback is not None  # geri bildirim ilk denemeden geçti, gösterilir
    reply = db.scalar(
        select(Event.payload).where(
            Event.activity_id == dialogue.activity.id, Event.type == "dialogue_replied"
        )
    )
    assert reply is not None and reply["source"] == "fallback"


def test_failed_feedback_is_hidden_and_never_retried_later(db: Session) -> None:
    dialogue = _start(db)
    leaky = ARTICLE.model_copy(update={"hint_tr": "Doğrusu: I am a teacher."})
    turn = DialogueTurn(feedback=leaky, partner=_turn().partner, done=False)
    _say(db, Partner(turn), dialogue, "I am teacher.")
    [shown] = service.view(db, dialogue).turns
    assert shown.feedback is None and shown.partner.en.startswith("Nice")
    writing = db.scalar(
        select(Event.id).where(
            Event.activity_id == dialogue.activity.id, Event.type == "writing_submitted"
        )
    )
    assert writing not in pending_writings(db)


def test_dialogue_endpoints(client: TestClient, sender: FakeSender, engine: object) -> None:
    _login(client, sender, engine)
    _consent(client)
    started = client.post("/api/practice/dialogue").json()
    assert started["opening"]["en"] and started["turns"] == []

    # Test istemcisinin sahte LLM'i diyalog şeması döndürmez: yedek cümleyle devam edilir.
    r = client.post(f"/api/practice/dialogue/{started['activity_id']}/reply", json={"text": "Hi!"})
    assert r.status_code == 200, r.text
    assert r.json()["turns"][0]["partner"]["en"] == service.FALLBACK_CONTINUE.en
    assert client.get(f"/api/practice/dialogue/{started['activity_id']}").json()["turns"]
    assert client.get("/api/practice/dialogue/999999").status_code == 404
