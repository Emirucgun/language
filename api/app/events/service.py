"""Olay yazmanın tek yolu: payload şemayla doğrulanır, kullanıcı kilidi alınır.

Kilit, tekrar motorunun filigranının olay sırasıyla tutarlı kalması için gerekir
(`app.scheduler.service.lock_user`). Commit çağırana aittir.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.events.models import Event
from app.events.schemas import CURRENT_VERSION, validate_payload
from app.scheduler.service import lock_user


def record_event(
    session: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    payload: dict[str, Any] | None = None,
    activity_id: int | None = None,
    item_id: int | None = None,
    rating: int | None = None,
    occurred_at: datetime | None = None,
) -> Event:
    data = payload or {}
    validate_payload(type, data)
    lock_user(session, user_id)
    event = Event(
        user_id=user_id,
        type=type,
        occurred_at=occurred_at or datetime.now(UTC),
        activity_id=activity_id,
        item_id=item_id,
        rating=rating,
        payload=data,
        schema_version=CURRENT_VERSION[type],
    )
    session.add(event)
    session.flush()
    return event
