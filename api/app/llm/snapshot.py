"""Öğrenci özeti: LLM'e giden tek "hafıza".

Hermes'teki MEMORY.md'nin karşılığı, ama LLM yazmaz: olaylardan ve türev tablolardan
deterministik üretilir, kısa tutulur (≤300 token) ve günde bir donar. Aynı bilgiden her
zaman aynı metin çıkar; metin hash'iyle bir kez saklanır ve çağrılar ona referans verir.
"""

import hashlib
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.models import User
from app.events.models import Event
from app.llm.models import LearnerSnapshot
from app.llm.prompts import estimate_tokens
from app.scheduler.models import ItemState

MAX_INTERESTS = 5
MAX_ERROR_CODES = 3
ERROR_WINDOW_DAYS = 30
REVIEW_STATE = 2  # fsrs.State.Review


@dataclass(frozen=True, slots=True)
class LearnerFacts:
    level: str | None
    goal: str | None
    daily_minutes: int | None
    interests: tuple[str, ...] = ()
    weak_skills: tuple[str, ...] = ()
    frequent_errors: tuple[tuple[str, int], ...] = field(default=())
    learned_items: int = 0


def render(facts: LearnerFacts) -> str:
    """Sabit sıralı, kısa İngilizce özet. Kimlik bilgisi içermez."""
    lines = ["Learner summary"]
    lines.append(f"Level: {facts.level or 'unknown'}")
    goal = facts.goal or "unspecified"
    if facts.daily_minutes:
        goal += f"; {facts.daily_minutes} min/day"
    lines.append(f"Goal: {goal}")
    if facts.interests:
        lines.append("Interests: " + ", ".join(sorted(facts.interests)[:MAX_INTERESTS]))
    if facts.weak_skills:
        lines.append("Weak skills: " + ", ".join(sorted(facts.weak_skills)))
    if facts.frequent_errors:
        top = facts.frequent_errors[:MAX_ERROR_CODES]
        lines.append("Frequent errors: " + ", ".join(f"{c} ({n})" for c, n in top))
    lines.append(f"Items learned: {facts.learned_items}")
    return "\n".join(lines)


def _latest_payload(session: Session, user_id: uuid.UUID, event_type: str) -> dict[str, object]:
    payload = session.scalar(
        select(Event.payload)
        .where(Event.user_id == user_id, Event.type == event_type)
        .order_by(Event.id.desc())
        .limit(1)
    )
    return payload or {}


def gather_facts(session: Session, user_id: uuid.UUID) -> LearnerFacts:
    user = session.get_one(User, user_id)
    placement = _latest_payload(session, user_id, "fixed_test_completed")
    goal = _latest_payload(session, user_id, "goal_set")

    errors = session.execute(
        text(
            "SELECT m.tag_code, count(*) AS n "
            "FROM learning.error_marks m "
            "JOIN learning.feedbacks f ON f.id = m.feedback_id "
            "JOIN learning.events e ON e.id = f.writing_event_id "
            "WHERE e.user_id = :uid AND f.created_at > now() - make_interval(days => :days) "
            "GROUP BY m.tag_code ORDER BY n DESC, m.tag_code LIMIT :lim"
        ),
        {"uid": user_id, "days": ERROR_WINDOW_DAYS, "lim": MAX_ERROR_CODES},
    ).all()

    learned = session.scalar(
        select(func.count())
        .select_from(ItemState)
        .where(ItemState.user_id == user_id, ItemState.state == REVIEW_STATE)
    )
    level = placement.get("cefr_estimate")
    weak = goal.get("weak_skills")
    return LearnerFacts(
        level=level if isinstance(level, str) else None,
        goal=user.goal,
        daily_minutes=user.daily_minutes,
        interests=tuple(user.interests),
        weak_skills=tuple(str(s) for s in weak) if isinstance(weak, list) else (),
        frequent_errors=tuple((str(code), int(n)) for code, n in errors),
        learned_items=learned or 0,
    )


def daily_snapshot(session: Session, user_id: uuid.UUID) -> LearnerSnapshot:
    """Kullanıcının bugünkü (kendi saat diliminde) donmuş özeti; yoksa şimdi üretilir.

    Gün içinde özet değişmez: aynı önek önbellekte kalır (Hermes'in oturum başı dondurması).
    """
    today = session.scalars(
        select(LearnerSnapshot)
        .where(
            LearnerSnapshot.user_id == user_id,
            text(
                "(learner_snapshots.created_at AT TIME ZONE users.timezone)::date "
                "= (now() AT TIME ZONE users.timezone)::date"
            ),
        )
        .join(User, User.id == LearnerSnapshot.user_id)
        .order_by(LearnerSnapshot.id.desc())
        .limit(1)
    ).first()
    return today or save_snapshot(session, user_id)


def save_snapshot(session: Session, user_id: uuid.UUID) -> LearnerSnapshot:
    """Özeti üretir; aynı metin daha önce kaydedildiyse o satırı döner."""
    body = render(gather_facts(session, user_id))
    digest = hashlib.sha256(body.encode()).digest()
    last_event_id = session.scalar(select(func.max(Event.id)).where(Event.user_id == user_id))
    session.execute(
        insert(LearnerSnapshot)
        .values(
            user_id=user_id,
            content_hash=digest,
            text=body,
            token_count=estimate_tokens(body),
            last_event_id=last_event_id,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "content_hash"])
    )
    return session.scalars(
        select(LearnerSnapshot).where(
            LearnerSnapshot.user_id == user_id, LearnerSnapshot.content_hash == digest
        )
    ).one()
