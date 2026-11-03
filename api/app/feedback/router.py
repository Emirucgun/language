from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import ConsentedUser, Db, get_llm_client
from app.feedback.service import FeedbackView, give_feedback, submit_rewrite
from app.llm.client import LLMClient

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class WritingRequest(BaseModel):
    task: str = Field(max_length=300)
    target_item_ids: list[int] = Field(min_length=1, max_length=5)
    text: str = Field(min_length=1, max_length=1000)
    activity_id: int | None = None


class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    activity_id: int | None = None


class RewriteResult(BaseModel):
    correction: str | None


@router.post("")
def post_writing(
    body: WritingRequest,
    db: Db,
    user: ConsentedUser,
    client: Annotated[LLMClient, Depends(get_llm_client)],
) -> FeedbackView:
    # Not: görev metni ve hedef öğeler, etkinlik üretimi gelince istemciden değil
    # `activity_id`'nin içeriğinden okunacak; şimdilik istemci gönderiyor.
    return give_feedback(
        db,
        client,
        user_id=user.id,
        task=body.task,
        target_item_ids=body.target_item_ids,
        learner_text=body.text.strip(),
        activity_id=body.activity_id,
    )


@router.post("/{feedback_id}/rewrite")
def post_rewrite(
    feedback_id: int, body: RewriteRequest, db: Db, user: ConsentedUser
) -> RewriteResult:
    try:
        correction = submit_rewrite(
            db,
            user_id=user.id,
            feedback_id=feedback_id,
            text=body.text.strip(),
            activity_id=body.activity_id,
        )
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Geri bildirim bulunamadı.") from exc
    return RewriteResult(correction=correction)
