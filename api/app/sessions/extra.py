"""Ek çalışma (blueprint, Bölüm 3 "Panel"): türü öğrenci seçer, öğeleri kural katmanı.

"Kullanıcı güçlü olduğu beceriyi seçse bile içerik zayıf ve vadesi gelen öğelerden gelir":
önce vadesi gelen tekrarlar, sonra en zorlanılan öğeler. Etkinlik seçildiği anda üretilir
(oturumla aynı hat: yeniden kullanım → Haiku → doğrulama → şablon). "Önerilen" tür,
müfredatın bu haftaki beceri ağırlığı ile bu hafta gerçekten ayrılan süre arasındaki en
büyük açıktır; öneri ile seçim ayrı kaydedilir (H7).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import Item
from app.curriculum.service import current_week, latest
from app.events.service import record_event
from app.llm.client import LLMClient
from app.onboarding.fixed_tests import user_level
from app.reports.service import compute, week_start_for
from app.scheduler.models import ItemState
from app.scheduler.service import select_items
from app.sessions.generation import SessionPlan, build_activities
from app.sessions.validation import ItemCard

ExtraKind = Literal["recall", "reading", "writing"]
# Ek çalışma türü → beceri (dinleme ve diyalog henüz yok).
SKILL_OF: dict[ExtraKind, str] = {
    "recall": "vocabulary",
    "reading": "reading",
    "writing": "writing",
}
ITEMS_FOR: dict[str, int] = {"recall": 4, "reading": 3}


class NothingToPractise(Exception):
    """Henüz hiç öğe görülmemiş: ek çalışma için önce bugünün oturumu."""


def recommend(db: Session, user: User) -> ExtraKind:
    curriculum = latest(db, user.id)
    weights: dict[str, float] = {"vocabulary": 0.3, "reading": 0.25, "writing": 0.25}
    if curriculum is not None:
        week = current_week(curriculum)
        for w in curriculum.weeks:
            if w["week"] == week:
                weights = {k: float(v) for k, v in w["skill_weights"].items()}
    minutes = compute(db, user, week_start_for(user, datetime.now(UTC))).minutes_by_skill
    total = sum(minutes.values())

    def gap(kind: ExtraKind) -> float:
        skill = SKILL_OF[kind]
        share = minutes.get(skill, 0.0) / total if total else 0.0
        return weights.get(skill, 0.0) - share

    # Eşitlikte kelime tekrarı (en ucuz ve en kalıcı etki).
    return max(("recall", "reading", "writing"), key=gap)


def _cards(db: Session, ids: list[int]) -> list[ItemCard]:
    items = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_(ids)))}
    return [
        ItemCard(i.id, i.text_en, i.text_tr, tuple(i.forms))
        for i in (items[x] for x in ids if x in items)
    ]


def practice_items(db: Session, user: User, count: int) -> list[int]:
    """Vadesi gelenler, sonra en zorlanılanlar (çok unutulan, düşük kararlılık)."""
    due = select_items(
        db,
        user.id,
        due_before=datetime.now(UTC) + timedelta(days=1),
        candidate_new_ids=[],
        max_reviews=count,
        max_new=0,
    ).review_item_ids
    if len(due) < count:
        weakest = db.scalars(
            select(ItemState.item_id)
            .where(ItemState.user_id == user.id, ItemState.item_id.not_in(due))
            .order_by(ItemState.lapses.desc(), ItemState.stability.asc().nulls_first())
            .limit(count - len(due))
        )
        due = [*due, *weakest]
    if not due:
        raise NothingToPractise(user.id)
    return due


def generate_extra(db: Session, client: LLMClient, user: User, kind: ExtraKind) -> list[int]:
    """Seçilen türde ek çalışma üretir; etkinlik id'lerini döner (okuma başarısızsa boş)."""
    if kind == "writing":
        raise ValueError("Yazma ek çalışması kendi uç noktasını kullanır.")
    recommended = recommend(db, user)
    cards = _cards(db, practice_items(db, user, ITEMS_FOR[kind]))
    _, cefr_sub = user_level(db, user.id)
    plan = (
        SessionPlan(review=cards, new=[], reading=[], writing=[], cefr_sub=cefr_sub)
        if kind == "recall"
        else SessionPlan(review=[], new=[], reading=cards, writing=[], cefr_sub=cefr_sub)
    )
    activity_ids = build_activities(
        db,
        client,
        user,
        plan,
        lexicon=None,
        origin="extra",
        session_id=None,
        recommended=kind == recommended,
        # Ek çalışma günde birkaç kez açılabilir: her üretimin şablonları ayrı içeriktir.
        template_salt=f"extra:{user.id}:{uuid.uuid4()}",
        purpose="extra",
    )
    record_event(
        db,
        user_id=user.id,
        type="extra_activity_chosen",
        payload={"recommended_kind": recommended, "chosen_kind": kind},
    )
    return activity_ids
