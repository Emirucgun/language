"""İlk gün: onam ve hedef anketi (blueprint, Bölüm 3, adım 1–2).

Her yanıt önce olay olarak yazılır; `users` üzerindeki alanlar yalnızca hızlı okuma
içindir ve olaylardan yeniden kurulabilir.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.router import Me
from app.config import settings
from app.deps import ConsentedUser, CurrentUser, Db
from app.events.schemas import GoalSet
from app.events.service import record_event

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class ConsentRequest(BaseModel):
    consent_version: str
    is_adult_confirmed: Literal[True]
    display_name: str | None = Field(default=None, max_length=80)


@router.post("/consent")
def give_consent(body: ConsentRequest, db: Db, user: CurrentUser) -> Me:
    if body.consent_version != settings.consent_version:
        raise HTTPException(status.HTTP_409_CONFLICT, "Onam metni güncellendi; yeniden okuyun.")
    now = datetime.now(UTC)
    record_event(
        db,
        user_id=user.id,
        type="consent_given",
        payload={"consent_version": body.consent_version, "is_adult_confirmed": True},
        occurred_at=now,
    )
    user.consent_version = body.consent_version
    user.consent_at = now
    user.is_adult_confirmed = True
    if body.display_name is not None:
        user.display_name = body.display_name.strip() or None
    return Me.of(user)


@router.post("/goals")
def set_goals(body: GoalSet, db: Db, user: ConsentedUser) -> Me:
    record_event(db, user_id=user.id, type="goal_set", payload=body.model_dump())
    user.goal = body.goal
    user.daily_minutes = body.daily_minutes
    user.interests = sorted({i.strip().lower() for i in body.interests if i.strip()})
    return Me.of(user)
