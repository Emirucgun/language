"""Yazma geri bildirimi akışı (blueprint, Bölüm 3, günlük döngü adım 4).

    öğrenci yazar → olay → LLM (Sonnet) → doğrulayıcı → feedbacks + error_marks
                  → doğruysa/yanlışsa derece olayı → tekrar motoru

Geri bildirim gösterilemezse (limit, API hatası, ret, doğrulayıcıdan kalma) öğrenci
"şimdilik atladık" görür; yazdığı metin olay kaydında durur ve sonra yeniden işlenir.
Doğru cümle ancak öğrenci yeniden yazdıktan sonra gösterilir.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.models import ErrorTag, Item
from app.events.models import Event
from app.events.service import record_event
from app.feedback import prompt as feedback_prompt
from app.feedback.llm_schema import WritingFeedback
from app.feedback.models import ErrorMark, Feedback
from app.llm.client import LLMClient
from app.llm.service import DailyLimitExceeded, Prompt, generate_structured
from app.llm.snapshot import daily_snapshot
from app.scheduler.engine import AnswerRating
from app.scheduler.service import update_item_states
from app.validator.core import Lexicon, ValidationResult, load_lexicon
from app.validator.feedback import shown_errors, span_of, validate_feedback

RECENT_CODES = 2


@dataclass(frozen=True, slots=True)
class ShownError:
    code: str
    name_tr: str
    explanation_tr: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class FeedbackView:
    """Öğrenciye dönen tek şey. Düzeltilmiş cümle burada yok (yeniden yazmadan sonra)."""

    status: Literal["shown", "deferred"]
    feedback_id: int | None
    writing_event_id: int
    is_correct: bool | None = None
    hint_tr: str | None = None
    errors: tuple[ShownError, ...] = ()


def _recent_codes(session: Session, user_id: uuid.UUID, item_ids: Sequence[int]) -> list[str]:
    rows = session.scalars(
        select(ErrorMark.tag_code)
        .join(Feedback, Feedback.id == ErrorMark.feedback_id)
        .join(Event, Event.id == Feedback.writing_event_id)
        .where(Event.user_id == user_id, Event.item_id.in_(item_ids))
        .order_by(ErrorMark.id.desc())
        .limit(RECENT_CODES)
    ).all()
    return list(rows)


def active_tags(session: Session) -> dict[str, ErrorTag]:
    tags = session.scalars(select(ErrorTag).where(ErrorTag.active)).all()
    return {t.code: t for t in tags}


def store_feedback(
    session: Session,
    *,
    writing_event_id: int,
    llm_call_id: int | None,
    status: str,
    validation: ValidationResult,
    parsed: WritingFeedback | None,
) -> Feedback:
    feedback = Feedback(
        writing_event_id=writing_event_id,
        llm_call_id=llm_call_id,
        status=status,
        hint_tr=parsed.hint_tr if parsed and status == "shown" else None,
        correction=parsed.correction if parsed and status == "shown" else None,
        validator_result=validation.to_dict(),
    )
    session.add(feedback)
    session.flush()
    if parsed and status == "shown":
        learner_text = str(session.get_one(Event, writing_event_id).payload["text"])
        shown = len(shown_errors(parsed))
        for index, error in enumerate(parsed.errors):
            # Doğrulayıcı her alıntının metinde bulunduğunu garanti eder.
            span = span_of(error, learner_text)
            assert span is not None
            session.add(
                ErrorMark(
                    feedback_id=feedback.id,
                    tag_code=error.code,
                    span_start=span[0],
                    span_end=span[1],
                    shown=index < shown,
                )
            )
        session.flush()
    return feedback


def give_feedback(
    session: Session,
    client: LLMClient,
    *,
    user_id: uuid.UUID,
    task: str,
    target_item_ids: Sequence[int],
    learner_text: str,
    activity_id: int | None = None,
    attempt: int = 1,
    lexicon: Lexicon | None = None,
) -> FeedbackView:
    """Öğrencinin yazdığı metni kaydeder ve doğrulanmış geri bildirimi döner.

    Commit çağırana aittir. Birincil hedef öğe (`target_item_ids[0]`) derecelendirilir.
    """
    writing = record_event(
        session,
        user_id=user_id,
        type="writing_submitted",
        payload={"text": learner_text, "attempt": attempt},
        activity_id=activity_id,
        item_id=target_item_ids[0] if target_item_ids else None,
    )
    return assess_writing(
        session,
        client,
        writing=writing,
        task=task,
        target_item_ids=target_item_ids,
        lexicon=lexicon,
    )


def assess_writing(
    session: Session,
    client: LLMClient,
    *,
    writing: Event,
    task: str,
    target_item_ids: Sequence[int],
    lexicon: Lexicon | None = None,
) -> FeedbackView:
    """Kaydedilmiş bir yazıyı değerlendirir: ilk gönderimde ve bekleyenler yeniden
    işlenirken aynı yol. Her deneme yeni bir `feedbacks` satırıdır (geçmiş korunur)."""
    user_id, activity_id = writing.user_id, writing.activity_id
    learner_text = str(writing.payload["text"])
    primary_item = target_item_ids[0] if target_item_ids else None

    items = session.scalars(select(Item).where(Item.id.in_(target_item_ids))).all()
    snapshot = daily_snapshot(session, user_id)
    prompt = Prompt(
        purpose="feedback",
        prompt_version=feedback_prompt.PROMPT_VERSION,
        static_block=feedback_prompt.static_block(session),
        snapshot_id=snapshot.id,
        snapshot_block=snapshot.text,
        task=feedback_prompt.task_block(
            task=task,
            target_items=[i.text_en for i in items],
            learner_text=learner_text,
            recent_codes=_recent_codes(session, user_id, target_item_ids),
        ),
    )

    validation = ValidationResult()
    try:
        parsed, call = generate_structured(
            session, client, prompt=prompt, output_type=WritingFeedback, user_id=user_id
        )
    except DailyLimitExceeded:
        validation.add("daily_limit", "kullanıcının günlük LLM limiti doldu")
        store_feedback(
            session,
            writing_event_id=writing.id,
            llm_call_id=None,
            status="deferred",
            validation=validation,
            parsed=None,
        )
        return FeedbackView(status="deferred", feedback_id=None, writing_event_id=writing.id)

    catalog = active_tags(session)
    if parsed is None:
        validation.add("llm_failed", call.status)
    else:
        validation = validate_feedback(
            parsed,
            learner_text=learner_text,
            catalog_codes=set(catalog),
            lexicon=lexicon or load_lexicon(session),
        )
    if parsed is None or not validation.ok:
        feedback = store_feedback(
            session,
            writing_event_id=writing.id,
            llm_call_id=call.id,
            status="rejected" if parsed else "deferred",
            validation=validation,
            parsed=parsed,
        )
        return FeedbackView(status="deferred", feedback_id=feedback.id, writing_event_id=writing.id)

    feedback = store_feedback(
        session,
        writing_event_id=writing.id,
        llm_call_id=call.id,
        status="shown",
        validation=validation,
        parsed=parsed,
    )
    if primary_item is not None:
        record_event(
            session,
            user_id=user_id,
            type="writing_assessed",
            payload={"feedback_id": feedback.id, "is_correct": parsed.is_correct},
            activity_id=activity_id,
            item_id=primary_item,
            rating=AnswerRating.GOOD if parsed.is_correct else AnswerRating.AGAIN,
        )
        update_item_states(session, user_id)

    return stored_view(session, feedback)


def stored_view(session: Session, feedback: Feedback) -> FeedbackView:
    """Kaydedilmiş geri bildirimin öğrenciye giden hali (gösterilen hatalar, katalog açıklaması)."""
    if feedback.status != "shown":
        return FeedbackView(
            status="deferred", feedback_id=feedback.id, writing_event_id=feedback.writing_event_id
        )
    catalog = active_tags(session)
    marks = session.scalars(
        select(ErrorMark)
        .where(ErrorMark.feedback_id == feedback.id, ErrorMark.shown)
        .order_by(ErrorMark.id)
    ).all()
    return FeedbackView(
        status="shown",
        feedback_id=feedback.id,
        writing_event_id=feedback.writing_event_id,
        is_correct=not marks and feedback.correction is None,
        hint_tr=feedback.hint_tr,
        errors=tuple(
            ShownError(
                code=m.tag_code,
                name_tr=catalog[m.tag_code].name_tr,
                explanation_tr=catalog[m.tag_code].explanation_tr,
                start=m.span_start,
                end=m.span_end,
            )
            for m in marks
        ),
    )


def submit_rewrite(
    session: Session,
    *,
    user_id: uuid.UUID,
    feedback_id: int,
    text: str,
    activity_id: int | None = None,
) -> str | None:
    """Öğrencinin yeniden yazdığı cümleyi kaydeder ve ancak şimdi doğru cümleyi döner."""
    feedback = session.get_one(Feedback, feedback_id)
    writing = session.get_one(Event, feedback.writing_event_id)
    if writing.user_id != user_id:
        raise PermissionError("Geri bildirim bu kullanıcıya ait değil.")
    attempt = int(writing.payload.get("attempt", 1)) + 1
    record_event(
        session,
        user_id=user_id,
        type="rewrite_submitted",
        payload={"text": text, "attempt": attempt},
        activity_id=activity_id,
        item_id=writing.item_id,
    )
    return feedback.correction
