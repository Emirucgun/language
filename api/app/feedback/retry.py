"""Bekleyen geri bildirimlerin yeniden işlenmesi (Technical MVP, 7: retry_deferred_feedback).

"Şimdilik atladık" denen yazılar (günlük limit, API hatası, ret, doğrulayıcıdan kalma)
saatlik işle yeniden değerlendirilir. Öğrenci hazır olanları panelde görür.

Sınırlar: yazı en fazla 7 günlük olmalı ve en fazla 3 deneme yapılır; sonra bırakılır
(Işıl'ın denetiminde "rejected" kayıtları olarak kalır).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.content.models import Item
from app.events.models import Event
from app.feedback.models import Feedback
from app.feedback.service import FeedbackView, assess_writing, stored_view
from app.llm.client import LLMClient
from app.sessions.models import Activity, ActivityContent
from app.sessions.schemas import Writing

MAX_AGE_DAYS = 7
MAX_ATTEMPTS = 3

_PENDING = text(
    """
    SELECT e.id
    FROM learning.events e
    WHERE e.type = 'writing_submitted'
      AND e.recorded_at > now() - make_interval(days => :age)
      AND NOT EXISTS (
        SELECT 1 FROM learning.feedbacks f WHERE f.writing_event_id = e.id AND f.status = 'shown'
      )
      AND (SELECT count(*) FROM learning.feedbacks f WHERE f.writing_event_id = e.id) < :attempts
      AND EXISTS (SELECT 1 FROM learning.feedbacks f WHERE f.writing_event_id = e.id)
    ORDER BY e.id
    """
)


def pending_writings(db: Session) -> list[int]:
    """Henüz gösterilmemiş, denemesi tükenmemiş yazılar. İlk denemesi hiç yapılmamış
    (feedback satırı olmayan) yazılar dahil değildir: onlar istek anında işlenir."""
    return list(db.scalars(_PENDING, {"age": MAX_AGE_DAYS, "attempts": MAX_ATTEMPTS}))


def _task_for(db: Session, writing: Event) -> tuple[str, list[int]]:
    """Görev metni kaydedilmez; etkinlikten ya da serbest pratik şablonundan yeniden kurulur."""
    if writing.activity_id is not None:
        content = db.scalar(
            select(ActivityContent.content)
            .join(Activity, Activity.content_id == ActivityContent.id)
            .where(Activity.id == writing.activity_id)
        )
        if content is not None:
            task = Writing.model_validate(content)
            return task.task_en, [task.item_id]
    item = db.get(Item, writing.item_id) if writing.item_id else None
    if item is None:
        return "Write one sentence about yourself.", []
    # app/sessions/router.py: writing_task ile aynı şablon.
    return f'Write one sentence about yourself using "{item.text_en}".', [item.id]


def retry_writing(db: Session, client: LLMClient, writing_event_id: int) -> FeedbackView | None:
    """Bir yazıyı yeniden değerlendirir; bu arada gösterilmişse ya da deneme bittiyse dokunmaz."""
    if writing_event_id not in pending_writings(db):
        return None
    writing = db.get_one(Event, writing_event_id)
    task, item_ids = _task_for(db, writing)
    return assess_writing(db, client, writing=writing, task=task, target_item_ids=item_ids)


@dataclass(frozen=True, slots=True)
class ReadyFeedback:
    """Sonradan hazırlanmış, öğrencinin henüz görmediği geri bildirim."""

    learner_text: str
    view: FeedbackView


def ready_for(db: Session, user_id: uuid.UUID) -> list[ReadyFeedback]:
    """Gecikmeli hazırlanan (öncesinde gösterilemeyen denemesi olan) ve henüz
    `feedback_shown` olayı yazılmamış geri bildirimler."""
    shown_ids = {
        int(p["feedback_id"])
        for p in db.scalars(
            select(Event.payload).where(Event.user_id == user_id, Event.type == "feedback_shown")
        )
        if p and p.get("feedback_id") is not None
    }
    attempts = (
        select(Feedback.writing_event_id, func.count().label("n"))
        .group_by(Feedback.writing_event_id)
        .subquery()
    )
    rows = db.execute(
        select(Feedback, Event)
        .join(Event, Event.id == Feedback.writing_event_id)
        .join(attempts, attempts.c.writing_event_id == Feedback.writing_event_id)
        .where(Event.user_id == user_id, Feedback.status == "shown", attempts.c.n > 1)
        .order_by(Feedback.id)
    ).all()
    return [
        ReadyFeedback(str(event.payload["text"]), stored_view(db, feedback))
        for feedback, event in rows
        if feedback.id not in shown_ids
    ]
