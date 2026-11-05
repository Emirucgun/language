"""Hatırlama testine (H1) hangi öğeler girer?

Hedef: ilk çalışmasının üzerinden en az 14 gün geçmiş öğeler. Son üç günde tekrar edilen
öğe girmez, çünkü taze tekrar kalıcılığı değil dünkü hatırayı ölçer. 28 günden eski öğe de
girmez: ölçtüğümüz şey "14 gün sonra" hatırlamak.

Kontrol: öğrencinin hiç çalışmadığı, hedeflerle aynı seviyede ve türde öğeler. Bu taban,
öğrencinin uygulamadan önce zaten bildiğini ya da tahminle bulduğunu gösterir.

Her öğe bir testte en fazla bir kez kullanılır. Seçim bu öğrenci ve gün için sabittir.
"""

import random
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.models import Item
from app.events.models import Event

STUDY_DAYS = 14
MAX_AGE_DAYS = 28
REST_DAYS = 3
MIN_TARGETS = 5
MAX_TARGETS = 12
CONTROLS = 3


@dataclass(frozen=True, slots=True)
class Studied:
    item_id: int
    first_at: datetime
    last_at: datetime


@dataclass(frozen=True, slots=True)
class Selection:
    targets: list[tuple[Item, Studied]]
    controls: list[Item]


def eligible(studied: Iterable[Studied], tested: set[int], now: datetime) -> list[Studied]:
    """Tarih kuralı: veritabanı olmadan sınanabilsin diye ayrı."""
    oldest = now - timedelta(days=MAX_AGE_DAYS)
    newest = now - timedelta(days=STUDY_DAYS)
    rested = now - timedelta(days=REST_DAYS)
    return [
        s
        for s in studied
        if s.item_id not in tested and oldest <= s.first_at <= newest and s.last_at <= rested
    ]


def _studied(db: Session, user_id: uuid.UUID) -> list[Studied]:
    rows = db.execute(
        select(Event.item_id, func.min(Event.occurred_at), func.max(Event.occurred_at))
        .where(Event.user_id == user_id, Event.rating.is_not(None), Event.item_id.is_not(None))
        .group_by(Event.item_id)
    )
    return [Studied(r[0], r[1], r[2]) for r in rows if r[0] is not None]


def _seen_items(db: Session, user_id: uuid.UUID) -> set[int]:
    """Olayı olan her öğe: derecelendirilmemiş karşılaşma da "çalışılmamış" sayılmaz."""
    rows = db.scalars(
        select(Event.item_id).where(Event.user_id == user_id, Event.item_id.is_not(None)).distinct()
    )
    return {item_id for item_id in rows if item_id is not None}


def select_items(
    db: Session,
    user_id: uuid.UUID,
    now: datetime,
    tested: set[int],
    usable: Callable[[Item], bool],
) -> Selection | None:
    """Yeterli hedef yoksa None: birkaç soruluk test oran üretmez, öğrenciyi de yorar."""
    rng = random.Random(f"{user_id}:{now.date()}")
    candidates = sorted(eligible(_studied(db, user_id), tested, now), key=lambda s: s.item_id)
    if len(candidates) < MIN_TARGETS:
        return None
    items = {
        item.id: item
        for item in db.scalars(
            select(Item).where(Item.id.in_([c.item_id for c in candidates]), Item.active)
        )
    }
    pairs = [(items[c.item_id], c) for c in candidates if c.item_id in items]
    pairs = [(item, c) for item, c in pairs if usable(item)]
    if len(pairs) < MIN_TARGETS:
        return None
    targets = rng.sample(pairs, min(MAX_TARGETS, len(pairs)))

    excluded = tested | _seen_items(db, user_id)
    pool = db.scalars(
        select(Item)
        .where(
            Item.active,
            Item.cefr.in_({item.cefr for item, _ in targets}),
            Item.kind.in_({item.kind for item, _ in targets}),
        )
        .order_by(Item.id)
    )
    unseen = [item for item in pool if item.id not in excluded and usable(item)]
    return Selection(targets, rng.sample(unseen, min(CONTROLS, len(unseen))))
