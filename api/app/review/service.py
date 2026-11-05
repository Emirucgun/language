"""Işıl'ın inceleme kuyruğu: önce "sorun var" işaretlileri, sonra rastgele örnek.

H4 yalnızca rastgele örneklemden hesaplanır: işaretli içerik zaten şüpheli olduğu için oranı
şişirir. Bu yüzden kaynak (`sample` / `flag`) istemciden alınmaz, burada belirlenir.

İnceleyen kimseyi görmez: öğrencinin metni gösterilir, kimliği gösterilmez.
"""

import random
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import ErrorTag, Item
from app.dialogue.scenarios import SCENARIOS
from app.dialogue.service import load_turns
from app.events.models import Event
from app.feedback.models import ErrorMark, Feedback
from app.reports.models import Review
from app.sessions.models import Activity, ActivityContent
from app.sessions.schemas import Choice, NewItem, Reading, Recall, Writing

TargetType = Literal["activity_content", "feedback"]
Verdict = Literal["correct", "wrong_teaching", "off_level", "unclear"]
Source = Literal["sample", "flag"]

SAMPLED_KINDS = ("recall", "new_item", "reading", "writing")
KIND_LABEL = {
    "recall": "Tekrar sorusu",
    "new_item": "Yeni öğe sunumu",
    "reading": "Okuma",
    "writing": "Yazma görevi",
    "dialogue": "Diyalog",
}

# Bir "sorun var" bayrağı, kendisinden sonra verilmiş inceleme kararı varsa kapanmıştır.
PENDING_FLAGS = text(
    """
    WITH flags AS (
      SELECT
        CASE WHEN e.payload->>'feedback_id' IS NOT NULL THEN 'feedback'
             ELSE 'activity_content' END AS target_type,
        COALESCE((e.payload->>'feedback_id')::int, a.content_id) AS target_id,
        e.recorded_at,
        e.payload->>'reason' AS reason
      FROM learning.events e
      LEFT JOIN learning.activities a ON a.id = e.activity_id
      WHERE e.type = 'activity_flagged'
    )
    SELECT f.target_type, f.target_id, f.reason
    FROM flags f
    WHERE f.target_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM learning.reviews r
        WHERE r.target_type = f.target_type
          AND r.target_id = f.target_id
          AND r.created_at >= f.recorded_at
      )
    ORDER BY f.recorded_at
    """
)


class TargetNotFound(Exception):
    pass


class AlreadyReviewed(Exception):
    pass


class ReviewLine(BaseModel):
    label: str
    text: str


class ReviewItem(BaseModel):
    target_type: TargetType
    target_id: int
    source: Source
    title: str
    level: str | None
    flag_reason: str | None
    lines: list[ReviewLine]


class ReviewStats(BaseModel):
    sample_reviewed: int
    sample_wrong_teaching: int
    flags_pending: int


@dataclass(frozen=True, slots=True)
class Target:
    target_type: TargetType
    target_id: int
    source: Source
    reason: str | None = None


def pending_flags(db: Session) -> list[Target]:
    """Aynı hedefin birden çok bayrağı tek kayda iner; en eski önce."""
    seen: set[tuple[str, int]] = set()
    targets: list[Target] = []
    for row in db.execute(PENDING_FLAGS):
        key = (row.target_type, row.target_id)
        if key not in seen:
            seen.add(key)
            targets.append(Target(row.target_type, row.target_id, "flag", row.reason))
    return targets


def _unreviewed(target_type: TargetType, target_id_column: object) -> object:
    return (
        ~select(Review.id)
        .where(
            Review.target_type == target_type,
            Review.target_id == target_id_column,
        )
        .exists()
    )


def _sample_content(db: Session) -> Target | None:
    """Şablonla üretilen içerik dışarıda: H4 üretilen içeriğin doğruluğunu ölçer."""
    target_id = db.scalar(
        select(ActivityContent.id)
        .where(
            ActivityContent.status == "approved",
            ActivityContent.model.is_not(None),
            ActivityContent.kind.in_(SAMPLED_KINDS),
            _unreviewed("activity_content", ActivityContent.id),  # type: ignore[arg-type]
        )
        .order_by(func.random())
        .limit(1)
    )
    return None if target_id is None else Target("activity_content", target_id, "sample")


def _sample_feedback(db: Session) -> Target | None:
    target_id = db.scalar(
        select(Feedback.id)
        .where(
            Feedback.status == "shown",
            _unreviewed("feedback", Feedback.id),  # type: ignore[arg-type]
        )
        .order_by(func.random())
        .limit(1)
    )
    return None if target_id is None else Target("feedback", target_id, "sample")


def next_target(db: Session) -> Target | None:
    flags = pending_flags(db)
    if flags:
        return flags[0]
    pickers = [_sample_content, _sample_feedback]
    random.shuffle(pickers)  # etkinlik ve geri bildirim eşit şansla
    return pickers[0](db) or pickers[1](db)


def _choice_lines(question: Choice, prefix: str = "Soru") -> list[ReviewLine]:
    return [
        ReviewLine(label=prefix, text=question.prompt),
        ReviewLine(label="Şıklar", text=" / ".join(question.options)),
        ReviewLine(label="Doğru cevap", text=question.answer),
    ]


def _item_line(db: Session, item_ids: list[int]) -> list[ReviewLine]:
    texts = db.scalars(select(Item.text_en).where(Item.id.in_(item_ids))).all()
    return [ReviewLine(label="Hedef öğe", text=", ".join(texts))] if texts else []


def _dialogue_lines(db: Session, content: ActivityContent) -> list[ReviewLine]:
    scenario = SCENARIOS[str(content.content["scenario"])]
    lines = [
        ReviewLine(label="Senaryo", text=scenario.scenario_tr),
        ReviewLine(label="Roller", text=f"{scenario.learner_role_tr} / {scenario.partner_role_tr}"),
        ReviewLine(label="Partner", text=scenario.opening_en),
    ]
    activity_id = db.scalar(select(Activity.id).where(Activity.content_id == content.id))
    if activity_id is not None:
        for turn in load_turns(db, activity_id):
            lines.append(ReviewLine(label="Öğrenci", text=turn.learner))
            lines.append(ReviewLine(label="Partner", text=str(turn.reply["partner_en"])))
    return lines


def _content_lines(db: Session, content: ActivityContent) -> list[ReviewLine]:
    lines = _item_line(db, content.item_ids)
    if content.kind == "recall":
        recall = Recall.model_validate(content.content)
        return [
            *lines,
            *_choice_lines(recall.question),
            ReviewLine(label="İpucu", text=recall.hint_tr),
        ]
    if content.kind == "new_item":
        item = NewItem.model_validate(content.content)
        examples = [
            ReviewLine(label=f"Örnek {n}", text=f"{e.en} ({e.tr})")
            for n, e in enumerate(item.examples, start=1)
        ]
        return [
            *lines,
            ReviewLine(label="Anlam", text=item.meaning_tr),
            *examples,
            *_choice_lines(item.check, "Kontrol sorusu"),
        ]
    if content.kind == "reading":
        reading = Reading.model_validate(content.content)
        lines = [*lines, ReviewLine(label="Metin", text=reading.text_en)]
        for number, question in enumerate(reading.questions, start=1):
            lines += _choice_lines(question, f"Soru {number}")
        return lines
    if content.kind == "writing":
        writing = Writing.model_validate(content.content)
        return [
            *lines,
            ReviewLine(label="Görev (Türkçe)", text=writing.task_tr),
            ReviewLine(label="Görev (İngilizce)", text=writing.task_en),
        ]
    return [*lines, *_dialogue_lines(db, content)]


def _feedback_lines(db: Session, feedback: Feedback) -> tuple[list[ReviewLine], str | None]:
    event = db.get_one(Event, feedback.writing_event_id)
    learner_text = str(event.payload["text"])
    lines: list[ReviewLine] = []
    level: str | None = None
    if event.activity_id is not None:
        content = db.scalar(
            select(ActivityContent)
            .join(Activity, Activity.content_id == ActivityContent.id)
            .where(Activity.id == event.activity_id)
        )
        if content is not None:
            level = content.cefr_sub
            lines += _item_line(db, content.item_ids)
            if content.kind == "writing":
                task = Writing.model_validate(content.content).task_tr
                lines.append(ReviewLine(label="Görev", text=task))
    lines.append(ReviewLine(label="Öğrencinin cümlesi", text=learner_text))

    marks = db.execute(
        select(ErrorMark, ErrorTag)
        .join(ErrorTag, ErrorTag.code == ErrorMark.tag_code)
        .where(ErrorMark.feedback_id == feedback.id, ErrorMark.shown)
        .order_by(ErrorMark.id)
    ).all()
    for mark, tag in marks:
        quote = learner_text[mark.span_start : mark.span_end]
        where = f" (“{quote}”)" if quote else ""
        lines.append(ReviewLine(label="Gösterilen hata", text=f"{tag.name_tr}{where}"))
    if not marks and feedback.correction is None:
        lines.append(ReviewLine(label="Sonuç", text="Cümle doğru kabul edildi."))
    if feedback.hint_tr:
        lines.append(ReviewLine(label="İpucu", text=feedback.hint_tr))
    if feedback.correction:
        lines.append(ReviewLine(label="Önerilen doğru cümle", text=feedback.correction))
    return lines, level


def render(db: Session, target: Target) -> ReviewItem:
    level: str | None
    if target.target_type == "activity_content":
        content = db.get_one(ActivityContent, target.target_id)
        title = KIND_LABEL.get(content.kind, content.kind)
        lines, level = _content_lines(db, content), content.cefr_sub
    else:
        feedback = db.get_one(Feedback, target.target_id)
        title = "Yazma geri bildirimi"
        lines, level = _feedback_lines(db, feedback)
    return ReviewItem(
        target_type=target.target_type,
        target_id=target.target_id,
        source=target.source,
        title=title,
        level=level,
        flag_reason=target.reason,
        lines=lines,
    )


def submit(
    db: Session,
    reviewer: User,
    *,
    target_type: TargetType,
    target_id: int,
    verdict: Verdict,
    notes: str | None,
) -> Review:
    model = ActivityContent if target_type == "activity_content" else Feedback
    row = db.get(model, target_id)
    if row is None:
        raise TargetNotFound

    flagged = any(
        (t.target_type, t.target_id) == (target_type, target_id) for t in pending_flags(db)
    )
    if not flagged and db.scalar(
        select(Review.id).where(Review.target_type == target_type, Review.target_id == target_id)
    ):
        raise AlreadyReviewed

    review = Review(
        target_type=target_type,
        target_id=target_id,
        reviewer=str(reviewer.id),
        verdict=verdict,
        source="flag" if flagged else "sample",
        notes=notes,
    )
    db.add(review)
    # Yanlış öğreten içerik başka öğrencilere dağıtılmaya devam etmesin.
    if verdict == "wrong_teaching" and isinstance(row, ActivityContent):
        row.status = "retired"
    db.flush()
    return review


def stats(db: Session) -> ReviewStats:
    sample = select(func.count()).select_from(Review).where(Review.source == "sample")
    return ReviewStats(
        sample_reviewed=db.scalar(sample) or 0,
        sample_wrong_teaching=db.scalar(sample.where(Review.verdict == "wrong_teaching")) or 0,
        flags_pending=len(pending_flags(db)),
    )
