"""Oturum üretimi: sahte LLM isteğe göre etkinlik üretir; doğrulayıcı ve kayıt gerçek."""

import os
import re
import uuid
from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.curriculum.schemas import CurriculumDraft
from app.llm.client import LLMRequest, LLMResult
from app.llm.pricing import Usage
from app.scheduler.models import ItemState
from app.sessions import service
from app.sessions.generation import ensure_session
from app.sessions.models import Activity, ActivityContent
from app.sessions.schemas import (
    AnswerRequest,
    Choice,
    Example,
    NewItem,
    Reading,
    Recall,
    SessionOutput,
    Writing,
)
from app.validator.core import Lexicon, words
from tests.conftest import _libpq_url

ITEMS = [("coffee", "kahve", []), ("every day", "her gün", []), ("work", "çalışmak", ["works"])]
READING_TEXT = (
    "Ali lives in Istanbul with his family. He is a teacher. He likes coffee and he drinks "
    "it every day before work. His school is near his home, so he walks there. After work "
    "he plays football with his friends in the park. In the evening he reads a book and "
    "drinks tea with his wife. He is a happy man."
)
LEXICON_WORDS = (
    "ali lives in istanbul with his family he is a teacher likes coffee and drinks it every "
    "day before work works his school near home so walks there after plays football friends "
    "the park evening reads book tea wife happy man i like live where does what london paris milk "
    "very much"
)
LEXICON = Lexicon(frozenset(LEXICON_WORDS.split()))
TODAY = date(2026, 11, 9)


class SessionFake:
    """Görevdeki [id] "metin" kartlarını okuyup her istenen etkinliği üretir.

    `leaky` içindeki öğeler için hatırlama sorusu cevabı soruda sızdırır (doğrulayıcı reddeder).
    """

    def __init__(self, leaky: set[int] | None = None, fail: bool = False) -> None:
        self.leaky = leaky or set()
        self.fail = fail
        self.tasks: list[str] = []

    @staticmethod
    def _cards(task: str, label: str) -> list[tuple[int, str]]:
        line = next(line for line in task.splitlines() if line.startswith(label))
        return [(int(i), t) for i, t in re.findall(r'\[(\d+)\] "([^"]+)"', line)]

    def _choice(self, item_id: int, target: str) -> Choice:
        prompt = (
            f"Ali likes {target} ___ very much."
            if item_id in self.leaky
            else "Ali likes ___ very much."
        )
        others = [o for o in ("tea", "milk", "football") if o != target][:2]
        return Choice(prompt=prompt, options=[target, *others], answer=target)

    def complete(self, request: LLMRequest) -> LLMResult:
        if request.output_type is CurriculumDraft:
            # Müfredat burada konu değil: çıktı yok → kural katmanı yedek planı kullanır.
            return LLMResult(request.config.model, None, Usage(0, 0), "max_tokens", 1, None)
        self.tasks.append(request.task)
        task = request.task
        output = None
        if not self.fail:
            output = SessionOutput(
                recall=[
                    Recall(item_id=i, question=self._choice(i, t), hint_tr="Ali bunu çok sever.")
                    for i, t in self._cards(task, "recall for:")
                ],
                new_items=[
                    NewItem(
                        item_id=i,
                        meaning_tr="Kısa anlam.",
                        examples=[
                            Example(en=f"I like {t}.", tr="x"),
                            Example(en=f"Ali likes {t}.", tr="y"),
                        ],
                        check=self._choice(i, t),
                    )
                    for i, t in self._cards(task, "new_item for:")
                ],
                reading=[]
                if "reading using: not requested" in task
                else [
                    Reading(
                        item_ids=[i for i, _ in self._cards(task, "reading using:")],
                        text_en=READING_TEXT,
                        questions=[
                            Choice(
                                prompt="Where does Ali live?",
                                options=["Istanbul", "London", "Paris"],
                                answer="Istanbul",
                            ),
                            Choice(
                                prompt="What does Ali like?",
                                options=["coffee", "tea", "milk"],
                                answer="coffee",
                            ),
                        ],
                    )
                ],
                writing=[
                    Writing(
                        item_id=i,
                        task_en=f'Write one sentence using "{t}".',
                        task_tr="Bir cümle yaz.",
                    )
                    for i, t in self._cards(task, "writing for:")
                ],
            )
        return LLMResult(
            model=request.config.model,
            parsed=output,
            usage=Usage(input_tokens=200, output_tokens=900),
            stop_reason="end_turn" if output else "max_tokens",
            latency_ms=4000,
            raw_text=None if output else "{",
        )


@pytest.fixture(scope="module")
def item_ids(migrated_db: Config) -> list[int]:
    # sublevel 0: havuz sırasında başa gelir, diğer testlerin öğelerinden önce seçilir.
    ids = []
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        for en, tr, forms in ITEMS:
            row = conn.execute(
                "INSERT INTO content.items "
                "(pool_version, kind, text_en, text_tr, cefr, sublevel, forms) "
                "VALUES ('test', 'word', %s, %s, 'A1', 0, %s) RETURNING id",
                (en, tr, forms),
            ).fetchone()
            assert row is not None
            ids.append(int(row[0]))
    return ids


@pytest.fixture
def db(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


def _user(db: Session, interests: str = "{football}") -> User:
    user_id = db.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes, interests, consent_at, "
            "is_adult_confirmed) VALUES (:e, 'work', 15, :i, now(), true) RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@example.com", "i": interests},
    ).scalar_one()
    return db.get_one(User, user_id)


def _kinds(db: Session, session_id: int) -> list[tuple[str, str]]:
    rows = db.execute(
        select(ActivityContent.kind, Activity.origin)
        .join(Activity, Activity.content_id == ActivityContent.id)
        .where(Activity.session_id == session_id)
        .order_by(Activity.position)
    ).all()
    return [(k, o) for k, o in rows]


def test_valid_output_builds_the_session_in_one_call(db: Session, item_ids: list[int]) -> None:
    user, fake = _user(db), SessionFake()
    study = ensure_session(db, fake, user, TODAY, lexicon=LEXICON)

    assert study.status == "ready" and len(fake.tasks) == 1
    assert _kinds(db, study.id) == [
        ("new_item", "session"),
        ("new_item", "session"),
        ("new_item", "session"),
        ("reading", "session"),
        ("writing", "session"),
    ]
    view = service.session_view(db, study)
    dumped = view.model_dump_json()
    assert '"answer"' not in dumped  # cevaplar öğrenciye gitmez
    assert view.activities[0].item_en == "coffee"

    # Aynı gün ikinci istek LLM'e gitmez.
    assert ensure_session(db, fake, user, TODAY, lexicon=LEXICON).id == study.id
    assert len(fake.tasks) == 1


def test_rejected_activity_is_retried_once_then_templated(db: Session, item_ids: list[int]) -> None:
    coffee = item_ids[0]
    user, fake = _user(db), SessionFake(leaky={coffee})
    study = ensure_session(db, fake, user, TODAY, lexicon=LEXICON)

    assert len(fake.tasks) == 2
    retry = fake.tasks[1]
    assert f'[{coffee}] "coffee"' in retry and "reading using: not requested" in retry
    kinds = _kinds(db, study.id)
    assert ("recall", "template") in kinds  # coffee için yedek şablon
    rejected = db.scalar(
        select(func.count())
        .select_from(ActivityContent)
        .where(ActivityContent.status == "rejected", ActivityContent.item_ids == [coffee])
    )
    # Reddedilen içerik denetim için saklanır; aynı içerik iki kez gelirse hash'le tek satır.
    assert rejected == 1


def test_llm_failure_falls_back_to_templates(db: Session, item_ids: list[int]) -> None:
    user, fake = _user(db), SessionFake(fail=True)
    study = ensure_session(db, fake, user, TODAY, lexicon=LEXICON)
    kinds = _kinds(db, study.id)
    assert len(fake.tasks) == 1  # ayrıştırılamayan çıktı tekrar denenmez
    assert all(origin == "template" for _, origin in kinds)
    assert ("reading", "template") not in kinds and study.status == "ready"


def test_short_activities_are_reused_across_learners(db: Session, item_ids: list[int]) -> None:
    first = _user(db)
    ensure_session(db, SessionFake(), first, TODAY, lexicon=LEXICON)
    second, fake = _user(db), SessionFake()
    ensure_session(db, fake, second, TODAY, lexicon=LEXICON)
    assert "new_item for: none" in fake.tasks[0]  # üçü de paylaşılan içerikten


def test_answers_are_graded_on_the_server_once(db: Session, item_ids: list[int]) -> None:
    user = _user(db, "{}")
    study = ensure_session(db, SessionFake(), user, date(2026, 11, 10), lexicon=LEXICON)
    view = service.session_view(db, study)
    new_item = view.activities[0]
    correct = new_item.questions[0].options[0]  # sahte çıktıda doğru şık başta

    result = service.answer(
        db, user.id, new_item.id, AnswerRequest(question_id="q0", answer=correct.upper())
    )
    assert result.correct
    state = db.get(ItemState, (user.id, item_ids[0]))
    assert state is not None and state.reps == 1

    with pytest.raises(service.AlreadyAnswered):
        service.answer(db, user.id, new_item.id, AnswerRequest(question_id="q0", answer="tea"))
    with pytest.raises(service.ActivityNotFound):
        service.answer(db, _user(db).id, new_item.id, AnswerRequest(question_id="q0", answer="x"))

    reading = next(a for a in view.activities if a.kind == "reading")
    wrong = service.answer(db, user.id, reading.id, AnswerRequest(question_id="q1", answer="tea"))
    assert not wrong.correct and wrong.correct_answer == "coffee"


def test_session_view_marks_done_and_completes(db: Session, item_ids: list[int]) -> None:
    user = _user(db, "{}")
    study = ensure_session(db, SessionFake(fail=True), user, date(2026, 11, 11), lexicon=LEXICON)
    view = service.session_view(db, study)
    for activity in view.activities:
        for q in activity.questions:
            service.answer(
                db, user.id, activity.id, AnswerRequest(question_id=q.id, answer=q.options[0])
            )
    remaining = [a for a in service.session_view(db, study).activities if not a.done]
    assert [a.kind for a in remaining] == ["writing"]  # yazma, metin gönderilince tamamlanır
    assert words("x") == ["x"]
