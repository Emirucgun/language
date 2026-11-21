"""İnceleme uç noktaları; yalnızca `reviewer` rolü."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import Db, ReviewerUser
from app.review import service
from app.review.service import ReviewItem, ReviewStats, TargetType, Verdict

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewQueueView(BaseModel):
    item: ReviewItem | None  # boşsa incelenecek bir şey kalmadı
    stats: ReviewStats


class ReviewRequest(BaseModel):
    target_type: TargetType
    target_id: int
    verdict: Verdict
    notes: str | None = Field(default=None, max_length=2000)


@router.get("/next")
def get_next(db: Db, _: ReviewerUser) -> ReviewQueueView:
    target = service.next_target(db)
    return ReviewQueueView(
        item=service.render(db, target) if target else None, stats=service.stats(db)
    )


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def post_review(body: ReviewRequest, db: Db, reviewer: ReviewerUser) -> None:
    try:
        service.submit(
            db,
            reviewer,
            target_type=body.target_type,
            target_id=body.target_id,
            verdict=body.verdict,
            notes=(body.notes or "").strip() or None,
        )
    except service.TargetNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "İncelenecek kayıt bulunamadı.") from exc
    except service.AlreadyReviewed as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu kayıt zaten incelendi.") from exc
