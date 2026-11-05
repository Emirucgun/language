"""Oturum üretimi: sahte LLM isteğe göre etkinlik üretir; doğrulayıcı ve kayıt gerçek."""

import os
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.curriculum.models import Curriculum
from app.curriculum.schemas import CurriculumDraft
from app.events.models import Event
from app.events.schemas import known_interests
from app.llm.client import LLMRequest, LLMResult
from app.llm.pricing import Usage
from app.scheduler.models import ItemState
from app.sessions import service
from app.sessions.generation import ensure_session, plan_session
from app.sessions.models import Activity, ActivityContent
from app.sessions.router import writing_task
from app.sessions.schemas import (
    OPTION_COUNT,
    AnswerRequest,
    Choice,
    Example,
    NewItem,
    Reading,
    Recall,
    SessionOutput,
    Writing,
)
from app.sessions.templates import recall_from_card
from app.sessions.validation import ItemCard, validate_reading
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
        others = [o for o in ("tea", "milk", "football", "book") if o != target][:3]
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
                                options=["Istanbul", "London", "Paris", "Ankara"],
                                answer="Istanbul",
                            ),
                            Choice(
                                prompt="What does Ali like?",
                                options=["coffee", "tea", "milk", "football"],
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
        # Yalnızca şablon çeldiricisi: dört şık için havuzda öğe olmalı; seçime girmesin diye sonda.
        for en in ("tea", "milk", "book"):
            conn.execute(
                "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, sublevel) "
                "VALUES ('test', 'word', %s, %s, 'A1', 9)",
                (en, en),
            )
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


def _state(db: Session, user: User, item_id: int, due: datetime) -> None:
    db.add(
        ItemState(
            user_id=user.id,
            item_id=item_id,
            state=2,
            stability=5.0,
            difficulty=5.0,
            due=due,
            last_review=due - timedelta(days=5),
            last_event_id=1,
        )
    )
    db.flush()


def test_items_due_later_today_are_selected_in_the_learners_time_zone(
    db: Session, item_ids: list[int]
) -> None:
    """03:00'te üretilen oturum gün içinde vadesi dolacakları da kapsar; yarınkileri almaz."""
    user = _user(db)
    user.timezone = "Asia/Tokyo"  # UTC+9: UTC gün sonu ile yerel gün sonu farklı
    zone = ZoneInfo(user.timezone)
    tonight, tomorrow, _ = item_ids
    _state(db, user, tonight, datetime.combine(TODAY, time(23, 30), zone))
    _state(db, user, tomorrow, datetime.combine(TODAY + timedelta(days=1), time(0, 30), zone))

    plan = plan_session(db, user, TODAY)

    assert [c.id for c in plan.review] == [tonight]


def _curriculum(db: Session, user: User, order: list[int]) -> None:
    weeks = [{"week": 1, "item_ids": order}]
    db.add(Curriculum(user_id=user.id, version=1, weeks=weeks, skill_weights={}))
    db.flush()


def test_free_writing_follows_the_curriculum(db: Session, item_ids: list[int]) -> None:
    user = _user(db)
    planned = item_ids[-1]  # havuz sırasında sonda
    _curriculum(db, user, [planned, *item_ids[:-1]])

    assert writing_task(db, user).target_item_ids == [planned]


def test_free_writing_skips_seen_items_in_curriculum_order(
    db: Session, item_ids: list[int]
) -> None:
    user = _user(db)
    first, second, _ = item_ids
    _curriculum(db, user, [first, second])
    _state(db, user, first, datetime.now(UTC) + timedelta(days=5))

    assert writing_task(db, user).target_item_ids == [second]


def test_free_writing_never_leaves_the_plan_when_everything_is_seen(
    db: Session, item_ids: list[int]
) -> None:
    user = _user(db)
    _curriculum(db, user, item_ids[:1])
    _state(db, user, item_ids[0], datetime.now(UTC) + timedelta(days=5))

    assert writing_task(db, user).target_item_ids == item_ids[:1]


def _reading(options: list[str]) -> Reading:
    question = Choice(prompt="Where does Ali live?", options=options, answer=options[0])
    return Reading(item_ids=[1], text_en=READING_TEXT, questions=[question, question])


def test_reading_questions_need_four_options_too() -> None:
    card = ItemCard(1, "coffee", "kahve", ())
    ok = validate_reading(_reading(["Istanbul", "London", "Paris", "Ankara"]), [card], LEXICON)
    short = validate_reading(_reading(["Istanbul", "London", "Paris"]), [card], LEXICON)
    assert "option_count" not in {i.code for i in ok.issues}
    assert "option_count" in {i.code for i in short.issues}


def test_template_recall_has_four_options_or_none() -> None:
    cards = [ItemCard(i, f"word{i}", f"k{i}", ()) for i in range(1, 8)]
    recall = recall_from_card(cards[0], cards)
    assert recall is not None
    assert len(recall.question.options) == OPTION_COUNT
    assert recall.question.answer in recall.question.options
    assert recall_from_card(cards[0], cards[:3]) is None  # az şıklı soru yerine soru yok


def test_template_distractors_do_not_depend_on_pool_order() -> None:
    cards = [ItemCard(i, f"word{i}", f"k{i}", ()) for i in range(1, 8)]
    first = recall_from_card(cards[0], cards)
    second = recall_from_card(cards[0], list(reversed(cards)))
    assert first == second


def test_options_are_shuffled_per_learner_but_stable(db: Session, item_ids: list[int]) -> None:
    """Model doğru cevabı neredeyse hep ilk şıkka koyuyordu (30 sorunun 29'u)."""
    options = ["answer", "b", "c", "d"]
    first_user, second_user = uuid.uuid4(), uuid.uuid4()
    orders = [
        service.shuffled(options, Activity(id=i, user_id=first_user), 0) for i in range(1, 41)
    ]
    assert all(sorted(order) == sorted(options) for order in orders)
    answer_first = sum(order[0] == "answer" for order in orders)
    assert answer_first < 20  # sabit yerde değil
    same = Activity(id=1, user_id=first_user)
    assert service.shuffled(options, same, 0) == service.shuffled(options, same, 0)
    others = [service.shuffled(options, Activity(id=1, user_id=second_user), i) for i in range(9)]
    assert len({tuple(order) for order in others}) > 1


def _stored_answer(db: Session, user: User, activity_id: int) -> str:
    _, content = service.owned_activity(db, user.id, activity_id)
    return service._questions(content.kind, content.content)[0].answer


def test_correct_choice_is_rated_by_the_items_stage(db: Session, item_ids: list[int]) -> None:
    """Öğrenme aşamasında Good, tekrar aşamasında Hard; yazılan derece olayda durur."""
    user = _user(db, "{}")
    study = ensure_session(db, SessionFake(), user, TODAY, lexicon=LEXICON)
    first, second = service.session_view(db, study).activities[:2]
    _, content = service.owned_activity(db, user.id, second.id)
    _state(db, user, content.item_ids[0], datetime.now(UTC) + timedelta(days=9))

    for activity in (first, second):
        answer = _stored_answer(db, user, activity.id)
        service.answer(db, user.id, activity.id, AnswerRequest(question_id="q0", answer=answer))

    ratings = db.execute(
        select(Event.activity_id, Event.rating).where(
            Event.user_id == user.id, Event.type == "answer_submitted"
        )
    ).all()
    assert dict(ratings) == {first.id: 3, second.id: 2}


def test_junk_interests_never_reach_the_learner_data(db: Session, item_ids: list[int]) -> None:
    """EK-9: serbest metin döneminden kalan uzun değer içeriği kırmaz."""
    user = _user(db, "{" + "x" * 80 + ",football}")
    study = ensure_session(db, SessionFake(), user, TODAY, lexicon=LEXICON)
    assert study.status == "ready"
    assert known_interests(user.interests) == ["football"]


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
    correct = _stored_answer(db, user, new_item.id)

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
