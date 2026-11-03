"""Haftalık rapor (blueprint, Bölüm 3 "Haftalık"): olay kaydından türetilir, yeniden üretilebilir.

Hafta, kullanıcının kendi saat diliminde pazartesi 00:00 – sonraki pazartesi 00:00'dır.
Rapor bir kez hesaplanıp `weekly_reports`'a yazılır (kullanıcının gördüğü hal); aynı
olaylardan aynı rapor çıkar.
"""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import ErrorTag
from app.events.models import Event
from app.feedback.models import ErrorMark, Feedback
from app.reports.models import WeeklyReport
from app.scheduler.models import ItemState
from app.sessions.models import Activity, ActivityContent

REVIEW_STATE = 2  # fsrs.State.Review
CONSOLIDATED_STABILITY_DAYS = 7  # ≥ 1 hafta hatırlanması beklenen öğe "kalıcılaştı" sayılır
SLOW_SUCCESS = 0.6
FAST_SUCCESS = 0.9


class TopError(BaseModel):
    code: str
    name_tr: str
    explanation_tr: str
    count: int


class WeeklyMetrics(BaseModel):
    week_start: date
    active_days: int
    sessions_completed: int
    new_items: int
    consolidated_items: int
    answers: int
    success_rate: float | None  # derecelendirilmiş cevaplarda Hard/Good/Easy oranı
    minutes_by_skill: dict[str, float]  # öneri ile seçim ayrımı H7 için ayrıca sayılır
    extra_chosen: int
    understood_rate: float | None  # H5: "anladım" oranı
    top_error: TopError | None

    @property
    def pace(self) -> str:
        """Yeniden planlamada tempo: yavaş / normal / hızlı."""
        if self.success_rate is None or self.answers < 5:
            return "normal"
        if self.success_rate < SLOW_SUCCESS:
            return "slow"
        if self.success_rate >= FAST_SUCCESS and self.sessions_completed >= 4:
            return "fast"
        return "normal"


def week_start_for(user: User, now: datetime) -> date:
    local = now.astimezone(ZoneInfo(user.timezone)).date()
    return local - timedelta(days=local.weekday())


def _window(user: User, week_start: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(user.timezone)
    start = datetime.combine(week_start, time.min, tz)
    return start, start + timedelta(days=7)


def compute(db: Session, user: User, week_start: date) -> WeeklyMetrics:
    start, end = _window(user, week_start)
    in_week = (Event.user_id == user.id, Event.recorded_at >= start, Event.recorded_at < end)
    tz = ZoneInfo(user.timezone)

    events = db.execute(
        select(
            Event.type,
            Event.recorded_at,
            Event.item_id,
            Event.rating,
            Event.payload,
            Event.activity_id,
        )
        .where(*in_week)
        .order_by(Event.id)
    ).all()
    active_days = len({e.recorded_at.astimezone(tz).date() for e in events})
    rated = [e for e in events if e.rating is not None and e.item_id is not None]

    # Bu hafta ilk kez derecelendirilen öğeler = yeni öğe.
    first_seen = {
        item_id: seen
        for item_id, seen in db.execute(
            select(Event.item_id, func.min(Event.recorded_at))
            .where(Event.user_id == user.id, Event.rating.is_not(None), Event.item_id.is_not(None))
            .group_by(Event.item_id)
        )
    }
    new_items = sum(1 for seen in first_seen.values() if start <= seen < end)

    consolidated = db.scalar(
        select(func.count())
        .select_from(ItemState)
        .where(
            ItemState.user_id == user.id,
            ItemState.state == REVIEW_STATE,
            ItemState.stability >= CONSOLIDATED_STABILITY_DAYS,
        )
    )

    # Beceri başına süre: cevap süreleri etkinlik türüne göre (yazma için sabit tahmin).
    kinds = {
        activity_id: kind
        for activity_id, kind in db.execute(
            select(Activity.id, ActivityContent.kind)
            .join(ActivityContent, ActivityContent.id == Activity.content_id)
            .where(Activity.id.in_({e.activity_id for e in events if e.activity_id}))
        )
    }
    skill_of = {
        "recall": "vocabulary",
        "new_item": "vocabulary",
        "reading": "reading",
        "listening": "listening",
        "writing": "writing",
        "dialogue": "writing",
    }
    minutes: defaultdict[str, float] = defaultdict(float)
    for e in events:
        if e.type == "answer_submitted" and e.activity_id in kinds:
            minutes[skill_of[kinds[e.activity_id]]] += (e.payload.get("duration_ms") or 0) / 60000
        elif e.type == "writing_submitted":
            minutes["writing"] += 1.5  # yazma süresi ölçülmüyor; ortalama tahmin

    reactions = [e.payload.get("understood") for e in events if e.type == "feedback_reaction"]

    top = db.execute(
        select(ErrorMark.tag_code, func.count().label("n"))
        .join(Feedback, Feedback.id == ErrorMark.feedback_id)
        .join(Event, Event.id == Feedback.writing_event_id)
        .where(*in_week, ErrorMark.tag_code != "OTHER")
        .group_by(ErrorMark.tag_code)
        .order_by(func.count().desc(), ErrorMark.tag_code)
        .limit(1)
    ).first()
    top_error = None
    if top is not None:
        tag = db.get_one(ErrorTag, top[0])
        top_error = TopError(
            code=tag.code, name_tr=tag.name_tr, explanation_tr=tag.explanation_tr, count=top[1]
        )

    return WeeklyMetrics(
        week_start=week_start,
        active_days=active_days,
        sessions_completed=sum(1 for e in events if e.type == "session_completed"),
        new_items=new_items,
        consolidated_items=consolidated or 0,
        answers=len(rated),
        success_rate=round(sum(1 for e in rated if e.rating >= 2) / len(rated), 2)
        if rated
        else None,
        minutes_by_skill={k: round(v, 1) for k, v in sorted(minutes.items())},
        extra_chosen=sum(1 for e in events if e.type == "extra_activity_chosen"),
        understood_rate=round(sum(1 for r in reactions if r) / len(reactions), 2)
        if reactions
        else None,
        top_error=top_error,
    )


def save(
    db: Session, user: User, metrics: WeeklyMetrics, extra: dict[str, Any] | None = None
) -> WeeklyReport:
    """Haftanın raporunu bir kez yazar; tekrar çağrılırsa mevcut raporu döner."""
    data = metrics.model_dump(mode="json") | (extra or {})
    db.execute(
        insert(WeeklyReport)
        .values(user_id=user.id, week_start=metrics.week_start, metrics=data)
        .on_conflict_do_nothing(index_elements=["user_id", "week_start"])
    )
    return db.scalars(
        select(WeeklyReport).where(
            WeeklyReport.user_id == user.id, WeeklyReport.week_start == metrics.week_start
        )
    ).one()


def latest_report(db: Session, user_id: uuid.UUID) -> WeeklyReport | None:
    return db.scalar(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == user_id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(1)
    )
