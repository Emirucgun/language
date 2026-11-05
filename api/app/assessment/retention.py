"""14 gün hatırlama testi (H1): kişiye özel, LLM'siz, şablonlu.

Öğrenciler farklı öğeleri farklı günlerde öğrenir; bu yüzden sabit bir test olamaz. Her
soru öğenin onaylı örnek cümlesinden kurulur: Türkçe çeviri ipucu, İngilizcede boşluk.
Testin tüm içeriği `retention_test_created` olayındadır, durum olaylardan okunur.

Ölçümdür, öğretim değil: doğru cevap gösterilmez, olaylar `item_id` ve derece taşımaz,
tekrar motoru cevapları görmez.
"""

import random
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.models import Item
from app.events.models import Event
from app.events.schemas import RetentionQuestion, RetentionTestCreated
from app.events.service import record_event
from app.onboarding.placement import normalize
from app.scheduler.retention import select_items
from app.scheduler.service import lock_user
from app.sessions.schemas import OPTION_COUNT

TEMPLATE_VERSION = 1
BLANK = "___"


class NoOpenTest(Exception):
    pass


class QuestionNotFound(Exception):
    pass


class AlreadyAnswered(Exception):
    pass


class RetentionQuestionView(BaseModel):
    """Öğrenciye giden hali: cevap ve soru grubu yok."""

    id: str
    sentence_en: str
    sentence_tr: str
    options: list[str]


@dataclass(frozen=True, slots=True)
class Score:
    target_correct: int
    target_total: int
    control_correct: int
    control_total: int


@dataclass(frozen=True, slots=True)
class OpenTest:
    test_id: str
    questions: list[RetentionQuestion]
    answered: dict[str, bool]


def cloze(item: Item) -> tuple[str, str] | None:
    """Öğenin yalın hâliyle geçtiği ilk örnek cümle: (boşluklu İngilizce, Türkçe).

    Çekimli hâl boşluğa konmaz: "goes" yanında yalın çeldiriciler cevabı ele verir.
    """
    term = re.compile(rf"(?<![\w']){re.escape(item.text_en)}(?![\w'])", re.IGNORECASE)
    for sentence in item.reference_sentences:
        blanked, count = term.subn(BLANK, sentence["en"])
        if count:
            return blanked, sentence["tr"]
    return None


def question_for(
    item: Item,
    pool: list[Item],
    user_id: uuid.UUID,
    group: Literal["target", "control"],
    first_studied: datetime | None = None,
) -> RetentionQuestion | None:
    """Çeldiriciler aynı tür ve seviyedendir; kurulamıyorsa soru yoktur, eksik şık olmaz."""
    sentence = cloze(item)
    if sentence is None:
        return None
    en, tr = sentence
    forms = {item.text_en.lower(), *(f.lower() for f in item.forms)}
    candidates = sorted(
        {
            other.text_en
            for other in pool
            if other.id != item.id
            and other.kind == item.kind
            and other.cefr == item.cefr
            and other.text_en.lower() not in forms
            and other.text_en.lower() not in en.lower()
        }
    )
    if len(candidates) < OPTION_COUNT - 1:
        return None
    rng = random.Random(f"{user_id}:{item.id}")
    options = [item.text_en, *rng.sample(candidates, OPTION_COUNT - 1)]
    rng.shuffle(options)
    return RetentionQuestion(
        id=f"q{item.id}",
        item_id=item.id,
        group=group,
        sentence_en=en,
        sentence_tr=tr,
        options=options,
        answer=item.text_en,
        first_studied=first_studied,
    )


def _created(db: Session, user_id: uuid.UUID) -> list[RetentionTestCreated]:
    payloads = db.scalars(
        select(Event.payload)
        .where(Event.user_id == user_id, Event.type == "retention_test_created")
        .order_by(Event.id)
    )
    return [RetentionTestCreated.model_validate(p) for p in payloads]


def _test_events(db: Session, user_id: uuid.UUID, event_type: str) -> list[dict[str, object]]:
    return list(
        db.scalars(
            select(Event.payload)
            .where(Event.user_id == user_id, Event.type == event_type)
            .order_by(Event.id)
        )
    )


def open_test(db: Session, user_id: uuid.UUID) -> OpenTest | None:
    tests = _created(db, user_id)
    if not tests:
        return None
    latest = tests[-1]
    completed = _test_events(db, user_id, "retention_test_completed")
    if any(p["test_id"] == latest.test_id for p in completed):
        return None
    answers = _test_events(db, user_id, "retention_test_answer")
    answered = {
        str(p["question_id"]): bool(p["correct"]) for p in answers if p["test_id"] == latest.test_id
    }
    return OpenTest(latest.test_id, latest.questions, answered)


def create_test(db: Session, user_id: uuid.UUID, now: datetime | None = None) -> str | None:
    """Yeterli öğe varsa testi açar. Açık test varken yenisini açmaz; tekrar çağrılabilir."""
    moment = now or datetime.now(UTC)
    lock_user(db, user_id)
    if open_test(db, user_id) is not None:
        return None
    tested = {q.item_id for test in _created(db, user_id) for q in test.questions}
    pool = list(db.scalars(select(Item).where(Item.active).order_by(Item.id)))

    def usable(item: Item) -> bool:
        return question_for(item, pool, user_id, "target") is not None

    selection = select_items(db, user_id, moment, tested, usable)
    if selection is None:
        return None
    questions = [
        question_for(item, pool, user_id, "target", studied.first_at)
        for item, studied in selection.targets
    ] + [question_for(item, pool, user_id, "control") for item in selection.controls]
    built = [q for q in questions if q is not None]
    # Kontroller sona yığılırsa öğrenci "son sorular zor" diye vazgeçer.
    random.Random(f"{user_id}:{moment.date()}").shuffle(built)
    test_id = str(uuid.uuid4())
    record_event(
        db,
        user_id=user_id,
        type="retention_test_created",
        payload=RetentionTestCreated(
            test_id=test_id, template_version=TEMPLATE_VERSION, questions=built
        ).model_dump(mode="json"),
        occurred_at=moment,
    )
    return test_id


def views(test: OpenTest) -> list[RetentionQuestionView]:
    return [RetentionQuestionView.model_validate(q.model_dump()) for q in test.questions]


def _score(test: OpenTest, answered: dict[str, bool]) -> Score:
    def count(group: str) -> tuple[int, int]:
        ids = [q.id for q in test.questions if q.group == group]
        return sum(answered.get(i, False) for i in ids), len(ids)

    return Score(*count("target"), *count("control"))


def answer(
    db: Session,
    user_id: uuid.UUID,
    question_id: str,
    given: str,
    duration_ms: int | None,
    now: datetime | None = None,
) -> Score | None:
    """Son soru cevaplanınca testi kapatır ve sonucu döner."""
    moment = now or datetime.now(UTC)
    lock_user(db, user_id)
    test = open_test(db, user_id)
    if test is None:
        raise NoOpenTest
    question = next((q for q in test.questions if q.id == question_id), None)
    if question is None:
        raise QuestionNotFound(question_id)
    if question_id in test.answered:
        raise AlreadyAnswered(question_id)
    correct = bool(given) and normalize(given) == normalize(question.answer)
    studied = question.first_studied
    record_event(
        db,
        user_id=user_id,
        type="retention_test_answer",
        payload={
            "test_id": test.test_id,
            "question_id": question_id,
            "item_id": question.item_id,
            "group": question.group,
            "answer": given,
            "correct": correct,
            "days_since_study": (moment - studied).days if studied else None,
            "duration_ms": duration_ms,
        },
        occurred_at=moment,
    )
    answered = test.answered | {question_id: correct}
    if len(answered) < len(test.questions):
        return None
    score = _score(test, answered)
    record_event(
        db,
        user_id=user_id,
        type="retention_test_completed",
        payload={
            "test_id": test.test_id,
            "target_correct": score.target_correct,
            "target_total": score.target_total,
            "control_correct": score.control_correct,
            "control_total": score.control_total,
        },
        occurred_at=moment,
    )
    return score
