"""Oturum görünümü (cevapsız) ve sunucu tarafı cevap değerlendirmesi.

Cevap her zaman sunucuda değerlendirilir; FSRS derecesini istemci belirleyemez.
Aynı soru iki kez değerlendirilmez (tekrar motoru aynı cevabı iki kez saymasın).
"""

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.models import Item
from app.events.models import Event
from app.events.service import record_event
from app.scheduler.engine import rating_for_answer
from app.scheduler.service import update_item_states
from app.sessions.models import Activity, ActivityContent, StudySession
from app.sessions.schemas import (
    ActivityView,
    AnswerRequest,
    AnswerResult,
    Choice,
    ChoiceView,
    Example,
    Kind,
    NewItem,
    Reading,
    Recall,
    SessionView,
)


class ActivityNotFound(Exception):
    pass


class AlreadyAnswered(Exception):
    pass


def _questions(kind: str, content: dict[str, Any]) -> list[Choice]:
    if kind == "recall":
        return [Recall.model_validate(content).question]
    if kind == "new_item":
        return [NewItem.model_validate(content).check]
    if kind == "reading":
        return Reading.model_validate(content).questions
    return []


def _answered(db: Session, activity_id: int) -> set[str]:
    rows = db.scalars(
        select(Event.payload["question_id"].astext).where(
            Event.activity_id == activity_id, Event.type == "answer_submitted"
        )
    )
    return {r for r in rows if r}


def _written(db: Session, activity_id: int) -> bool:
    return (
        db.scalar(
            select(Event.id)
            .where(Event.activity_id == activity_id, Event.type == "writing_submitted")
            .limit(1)
        )
        is not None
    )


def activity_view(db: Session, activity: Activity, content: ActivityContent) -> ActivityView:
    kind: Kind = content.kind  # type: ignore[assignment]
    data = content.content
    questions = _questions(kind, data)
    answered = _answered(db, activity.id)
    view = ActivityView(
        id=activity.id,
        kind=kind,
        recommended=activity.recommended,
        done=_written(db, activity.id)
        if kind == "writing"
        else all(f"q{i}" in answered for i in range(len(questions))),
        questions=[
            ChoiceView(id=f"q{i}", prompt=q.prompt, options=q.options)
            for i, q in enumerate(questions)
        ],
    )
    if kind == "recall":
        view.hint_tr = data["hint_tr"]
    elif kind == "new_item":
        item = db.get(Item, data["item_id"])
        view.item_en = item.text_en if item else None
        view.meaning_tr = data["meaning_tr"]
        view.examples = [Example.model_validate(e) for e in data["examples"]]
    elif kind == "reading":
        view.text_en = data["text_en"]
    elif kind == "writing":
        view.task_tr = data["task_tr"]
    return view


def session_view(db: Session, study: StudySession) -> SessionView:
    rows = db.execute(
        select(Activity, ActivityContent)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(Activity.session_id == study.id)
        .order_by(Activity.position)
    ).all()
    return SessionView(
        id=study.id,
        local_date=study.local_date.isoformat(),
        status=study.status,
        activities=[activity_view(db, a, c) for a, c in rows],
    )


def owned_activity(
    db: Session, user_id: uuid.UUID, activity_id: int
) -> tuple[Activity, ActivityContent]:
    row = db.execute(
        select(Activity, ActivityContent)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(Activity.id == activity_id, Activity.user_id == user_id)
    ).first()
    if row is None:
        raise ActivityNotFound(activity_id)
    return row[0], row[1]


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def answer(db: Session, user_id: uuid.UUID, activity_id: int, req: AnswerRequest) -> AnswerResult:
    activity, content = owned_activity(db, user_id, activity_id)
    questions = _questions(content.kind, content.content)
    index = int(req.question_id[1:]) if req.question_id[1:].isdigit() else -1
    if not req.question_id.startswith("q") or not 0 <= index < len(questions):
        raise ActivityNotFound(req.question_id)
    if req.question_id in _answered(db, activity_id):
        raise AlreadyAnswered(req.question_id)

    question = questions[index]
    correct = normalize(req.answer) == normalize(question.answer)
    # Okuma soruları tek bir öğeye bağlı değil: derecelendirilmez, yalnızca kaydedilir.
    item_id = content.item_ids[0] if content.kind in ("recall", "new_item") else None
    record_event(
        db,
        user_id=user_id,
        type="answer_submitted",
        payload={
            "question_id": req.question_id,
            "answer": req.answer,
            "correct": correct,
            "duration_ms": req.duration_ms,
        },
        activity_id=activity.id,
        item_id=item_id,
        rating=rating_for_answer(correct=correct, hinted=req.hinted) if item_id else None,
    )
    if item_id:
        update_item_states(db, user_id)
    complete_if_done(db, activity)
    return AnswerResult(correct=correct, correct_answer=question.answer)


def complete_if_done(db: Session, activity: Activity) -> None:
    if activity.session_id is None:
        return
    study = db.get_one(StudySession, activity.session_id)
    rows = db.execute(
        select(Activity, ActivityContent)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(Activity.session_id == study.id)
    ).all()
    if all(activity_view(db, a, c).done for a, c in rows) and study.status != "completed":
        study.status = "completed"
        record_event(
            db, user_id=study.user_id, type="session_completed", payload={"session_id": study.id}
        )
