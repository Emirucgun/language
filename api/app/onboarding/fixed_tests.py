"""Sabit testlerin akışı: soru görünümü, cevap kaydı, tamamlama ve seviye.

Her cevap `fixed_test_answer` olayıdır; sonuç da bu olaylardan hesaplanıp
`fixed_test_completed` olayı olarak yazılır. Test sırasında doğru cevap gösterilmez ve
cevaplar tekrar motorunu etkilemez (ölçüm, öğretim değil). Aynı soru iki kez cevaplanmaz,
aynı test iki kez tamamlanmaz.
"""

import random
import uuid
from dataclasses import dataclass

from sqlalchemy import Integer, cast, select
from sqlalchemy.orm import Session

from app.content.models import FixedTest
from app.events.models import Event
from app.events.schemas import FixedTestCompleted
from app.events.service import record_event
from app.onboarding.placement import FixedQuestion, FixedQuestionView, Placement, is_correct, score

DEFAULT_LEVEL = ("A1", "A1.1")


class TestNotFound(Exception):
    pass


class AlreadyAnswered(Exception):
    pass


class QuestionNotFound(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TestState:
    test: FixedTest
    questions: list[FixedQuestion]
    answered: set[str]
    result: Placement | None


def current_test(db: Session, purpose: str) -> FixedTest:
    test = db.scalar(
        select(FixedTest)
        .where(FixedTest.purpose == purpose)
        .order_by(FixedTest.version.desc())
        .limit(1)
    )
    if test is None:
        raise TestNotFound(purpose)
    return test


def _events(db: Session, user_id: uuid.UUID, test_id: int, event_type: str) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(
                Event.user_id == user_id,
                Event.type == event_type,
                cast(Event.payload["test_id"].astext, Integer) == test_id,
            )
            .order_by(Event.id)
        )
    )


def _result_from_payload(payload: dict[str, object]) -> Placement:
    done = FixedTestCompleted.model_validate(payload)
    estimate = done.cefr_estimate if done.cefr_estimate in ("pre-A1", "A1", "A2") else "A1"
    return Placement(
        cefr_estimate=estimate,  # type: ignore[arg-type]
        sublevel=done.sublevel or 1,
        level_scores=done.level_scores or {},
        score=done.score,
    )


def state(db: Session, user_id: uuid.UUID, purpose: str) -> TestState:
    test = current_test(db, purpose)
    questions = [FixedQuestion.model_validate(q) for q in test.questions]
    answered = {
        str(e.payload["question_id"]) for e in _events(db, user_id, test.id, "fixed_test_answer")
    }
    completed = _events(db, user_id, test.id, "fixed_test_completed")
    result = _result_from_payload(completed[-1].payload) if completed else None
    return TestState(test, questions, answered, result)


def views(questions: list[FixedQuestion], user_id: uuid.UUID) -> list[FixedQuestionView]:
    """Şıklar kullanıcıya özgü ama sabit sırayla karışık: doğru cevap hep aynı yerde olmasın,
    test yarıda bırakılıp dönüldüğünde de sıra değişmesin."""
    result = []
    for q in questions:
        options = list(q.options)
        random.Random(f"{user_id}:{q.id}").shuffle(options)
        result.append(FixedQuestionView.model_validate(q.model_dump() | {"options": options}))
    return result


def answer(
    db: Session,
    user_id: uuid.UUID,
    purpose: str,
    question_id: str,
    given: str,
    duration_ms: int | None,
) -> None:
    current = state(db, user_id, purpose)
    question = next((q for q in current.questions if q.id == question_id), None)
    if question is None:
        raise QuestionNotFound(question_id)
    if current.result is not None or question_id in current.answered:
        raise AlreadyAnswered(question_id)
    record_event(
        db,
        user_id=user_id,
        type="fixed_test_answer",
        payload={
            "test_id": current.test.id,
            "question_id": question_id,
            "answer": given,
            "correct": is_correct(question, given),
            "duration_ms": duration_ms,
        },
    )


def complete(db: Session, user_id: uuid.UUID, purpose: str) -> Placement:
    """Sonucu cevap olaylarından hesaplar; daha önce tamamlandıysa aynı sonucu döner."""
    current = state(db, user_id, purpose)
    if current.result is not None:
        return current.result
    answers = {
        str(e.payload["question_id"]): str(e.payload["answer"])
        for e in _events(db, user_id, current.test.id, "fixed_test_answer")
    }
    result = score(current.questions, answers)
    record_event(
        db,
        user_id=user_id,
        type="fixed_test_completed",
        payload={
            "test_id": current.test.id,
            "score": round(result.score, 3),
            "cefr_estimate": result.cefr_estimate,
            "sublevel": result.sublevel,
            "level_scores": {k: round(v, 3) for k, v in result.level_scores.items()},
        },
    )
    return result


def placement_result(db: Session, user_id: uuid.UUID) -> Placement | None:
    """Kullanıcının en son yerleştirme sonucu (her test sürümünde)."""
    payload = db.scalar(
        select(Event.payload)
        .join(FixedTest, FixedTest.id == cast(Event.payload["test_id"].astext, Integer))
        .where(
            Event.user_id == user_id,
            Event.type == "fixed_test_completed",
            FixedTest.purpose == "placement",
        )
        .order_by(Event.id.desc())
        .limit(1)
    )
    return _result_from_payload(payload) if payload else None


def user_level(db: Session, user_id: uuid.UUID) -> tuple[str, str]:
    """(başlangıç seviyesi, alt seviye): etkinlik üretimi için. Test yoksa A1.1."""
    result = placement_result(db, user_id)
    return (result.start_level, result.cefr_sub) if result else DEFAULT_LEVEL
