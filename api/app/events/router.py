"""İstemcinin doğrudan bildirebileceği olaylar (gösterim, tepki, işaretleme, NPS...).

Derecelendirilmiş olaylar (`rating`) buradan yazılamaz: dereceyi her zaman sunucu
kuralları belirler. Etkinlik sahipliği kontrol edilir.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.deps import ConsentedUser, Db
from app.events.service import record_event
from app.sessions.models import Activity

router = APIRouter(prefix="/api/events", tags=["events"])

CLIENT_EVENT_TYPES = frozenset(
    {
        "activity_shown",
        "feedback_shown",
        "feedback_reaction",
        "activity_flagged",
        "extra_activity_chosen",
        "session_completed",
        "report_viewed",
        "nps_submitted",
    }
)


class ClientEvent(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    activity_id: int | None = None
    occurred_at: datetime | None = None


class Recorded(BaseModel):
    id: int


@router.post("", status_code=status.HTTP_201_CREATED)
def post_event(body: ClientEvent, db: Db, user: ConsentedUser) -> Recorded:
    if body.type not in CLIENT_EVENT_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bu olay türü kabul edilmez.")
    if body.activity_id is not None:
        owner = db.scalar(select(Activity.user_id).where(Activity.id == body.activity_id))
        if owner != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Etkinlik bulunamadı.")
    try:
        event = record_event(
            db,
            user_id=user.id,
            type=body.type,
            payload=body.payload,
            activity_id=body.activity_id,
            occurred_at=body.occurred_at,
        )
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, exc.errors(include_url=False)
        ) from exc
    return Recorded(id=event.id)
