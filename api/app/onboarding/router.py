"""İlk gün: onam, hedef anketi ve yerleştirme testi (blueprint, Bölüm 3, adım 1–3).

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
from app.onboarding import fixed_tests
from app.onboarding.placement import FixedQuestionView, Placement

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
    return Me.of(db, user)


@router.post("/goals")
def set_goals(body: GoalSet, db: Db, user: ConsentedUser) -> Me:
    record_event(db, user_id=user.id, type="goal_set", payload=body.model_dump())
    user.goal = body.goal
    user.daily_minutes = body.daily_minutes
    user.interests = sorted(set(body.interests))
    return Me.of(db, user)


# --- Yerleştirme testi ---------------------------------------------------------


class PlacementResult(BaseModel):
    cefr_estimate: str
    sublevel: int
    score: float


class PlacementView(BaseModel):
    version: int
    questions: list[FixedQuestionView]
    answered: list[str]
    result: PlacementResult | None


class PlacementAnswer(BaseModel):
    question_id: str = Field(max_length=16)
    answer: str = Field(max_length=200)  # boş: "bilmiyorum"
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


def _result(p: Placement | None) -> PlacementResult | None:
    if p is None:
        return None
    return PlacementResult(cefr_estimate=p.cefr_estimate, sublevel=p.sublevel, score=p.score)


@router.get("/placement")
def get_placement(db: Db, user: ConsentedUser) -> PlacementView:
    try:
        current = fixed_tests.state(db, user.id, "placement")
    except fixed_tests.TestNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleştirme testi yüklenmedi.") from exc
    return PlacementView(
        version=current.test.version,
        questions=fixed_tests.views(current.questions, user.id),
        answered=sorted(current.answered),
        result=_result(current.result),
    )


@router.post("/placement/answer", status_code=status.HTTP_204_NO_CONTENT)
def post_placement_answer(body: PlacementAnswer, db: Db, user: ConsentedUser) -> None:
    try:
        fixed_tests.answer(
            db, user.id, "placement", body.question_id, body.answer.strip(), body.duration_ms
        )
    except fixed_tests.QuestionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Soru bulunamadı.") from exc
    except fixed_tests.AlreadyAnswered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu soru zaten cevaplandı.") from exc


@router.post("/placement/complete")
def complete_placement(db: Db, user: ConsentedUser) -> PlacementResult:
    result = _result(fixed_tests.complete(db, user.id, "placement"))
    assert result is not None
    return result
