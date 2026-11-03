"""Olaylardan `item_states` türetme ve çalışılacak öğe seçimi.

Tek doğruluk kaynağı `events`: derecelendirilmiş her olay (`item_id` ve `rating` dolu)
`id` sırasıyla FSRS'e uygulanır. Her öğe satırı işlediği son olayı (`last_event_id`)
tutar; artımlı güncelleme oradan devam eder, yeniden oynatma sıfırdan başlar ve ikisi
aynı sonucu vermek zorundadır.
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.events.models import Event
from app.scheduler.engine import CardState, apply_review
from app.scheduler.models import ItemState

RatedEvent = tuple[int, int, int, datetime]  # (event_id, item_id, rating, recorded_at)
States = dict[int, tuple[CardState, int]]  # item_id -> (durum, son olay id'si)


def lock_user(session: Session, user_id: uuid.UUID) -> None:
    """Kullanıcı başına işlem kilidi (transaction sonunda bırakılır).

    Derecelendirilmiş olay yazan kod da bu kilidi almalı: olay ekleme ve durum
    güncellemesi aynı kullanıcı için sıralı olursa, sıra numarası küçük bir olayın
    filigranın gerisinde kalıp atlanması mümkün olmaz. Kaçan bir durum olursa
    `find_mismatches` yakalar.
    """
    session.execute(select(func.pg_advisory_xact_lock(func.hashtext(str(user_id)))))


def _to_state(row: ItemState) -> CardState:
    return CardState(
        state=row.state,
        step=row.step,
        stability=row.stability,
        difficulty=row.difficulty,
        due=row.due,
        last_review=row.last_review,
        reps=row.reps,
        lapses=row.lapses,
    )


def fold_events(events: Iterable[RatedEvent], start: States | None = None) -> States:
    """Olayları sırayla uygular; daha önce işlenmiş olaylar atlanır."""
    states = dict(start or {})
    for event_id, item_id, rating, recorded_at in events:
        previous = states.get(item_id)
        if previous is not None and event_id <= previous[1]:
            continue
        states[item_id] = (
            apply_review(previous[0] if previous else None, rating, recorded_at),
            event_id,
        )
    return states


def _rated_events(session: Session, user_id: uuid.UUID, after_id: int = 0) -> list[RatedEvent]:
    rows = session.execute(
        select(Event.id, Event.item_id, Event.rating, Event.recorded_at)
        .where(
            Event.user_id == user_id,
            Event.item_id.is_not(None),
            Event.rating.is_not(None),
            Event.id > after_id,
        )
        .order_by(Event.id)
    ).all()
    events: list[RatedEvent] = []
    for event_id, item_id, rating, recorded_at in rows:
        assert item_id is not None and rating is not None  # sorgu filtresi garanti eder
        events.append((event_id, item_id, rating, recorded_at))
    return events


def _stored_states(session: Session, user_id: uuid.UUID) -> States:
    rows = session.scalars(select(ItemState).where(ItemState.user_id == user_id)).all()
    return {row.item_id: (_to_state(row), row.last_event_id) for row in rows}


def _upsert(session: Session, user_id: uuid.UUID, states: States) -> None:
    if not states:
        return
    values = [
        {
            "user_id": user_id,
            "item_id": item_id,
            "state": s.state,
            "step": s.step,
            "stability": s.stability,
            "difficulty": s.difficulty,
            "due": s.due,
            "last_review": s.last_review,
            "reps": s.reps,
            "lapses": s.lapses,
            "last_event_id": last_event_id,
        }
        for item_id, (s, last_event_id) in states.items()
    ]
    stmt = insert(ItemState).values(values)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[ItemState.user_id, ItemState.item_id],
            set_={c: stmt.excluded[c] for c in values[0] if c not in ("user_id", "item_id")},
        )
    )


def update_item_states(session: Session, user_id: uuid.UUID) -> int:
    """Yeni derecelendirmeleri uygular; güncellenen öğe sayısını döner.

    Commit çağırana aittir.
    """
    lock_user(session, user_id)
    stored = _stored_states(session, user_id)
    # En eski filigrandan sonrası yeterli; daha önce işlenmiş olaylar fold'da atlanır.
    after_id = min((last for _, last in stored.values()), default=0)
    updated = fold_events(_rated_events(session, user_id, after_id), stored)
    changed = {k: v for k, v in updated.items() if stored.get(k) != v}
    _upsert(session, user_id, changed)
    return len(changed)


def rebuild_item_states(session: Session, user_id: uuid.UUID) -> int:
    """Öğrenci modelini olay kaydından sıfırdan yeniden hesaplayıp yazar."""
    lock_user(session, user_id)
    rebuilt = fold_events(_rated_events(session, user_id))
    _upsert(session, user_id, rebuilt)
    return len(rebuilt)


def find_mismatches(session: Session, user_id: uuid.UUID) -> list[int]:
    """Kayıtlı durumu yeniden oynatmayla karşılaştırır; uyuşmayan öğe id'lerini döner."""
    stored = _stored_states(session, user_id)
    rebuilt = fold_events(_rated_events(session, user_id))
    return sorted(k for k in stored.keys() | rebuilt.keys() if stored.get(k) != rebuilt.get(k))


@dataclass(frozen=True, slots=True)
class Selection:
    review_item_ids: list[int]
    new_item_ids: list[int]


def select_items(
    session: Session,
    user_id: uuid.UUID,
    *,
    due_before: datetime,
    candidate_new_ids: Sequence[int],
    max_reviews: int,
    max_new: int,
) -> Selection:
    """Bugün çalışılacak öğeler: önce vadesi gelenler (en gecikmiş önce), sonra yeniler.

    `candidate_new_ids` müfredatın bu haftaki sırasıdır; görülmüş öğeler atlanır.
    Tekrar birikmişse yeni öğe kotası yarıya iner, böylece günlük süre aşılmaz.
    """
    due = session.scalars(
        select(ItemState.item_id)
        .where(ItemState.user_id == user_id, ItemState.due <= due_before)
        .order_by(ItemState.due, ItemState.item_id)
        .limit(max_reviews)
    ).all()

    seen = set(
        session.scalars(
            select(ItemState.item_id).where(
                and_(ItemState.user_id == user_id, ItemState.item_id.in_(candidate_new_ids))
            )
        ).all()
    )
    backlog = len(due) >= max_reviews
    new_quota = max_new // 2 if backlog else max_new
    new = [i for i in candidate_new_ids if i not in seen][:new_quota]
    return Selection(review_item_ids=list(due), new_item_ids=new)
