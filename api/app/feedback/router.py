from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import ConsentedUser, Db, get_llm_client
from app.feedback.service import FeedbackView, give_feedback, submit_rewrite
from app.llm.client import LLMClient
from app.sessions import service as sessions
from app.sessions.schemas import Writing

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class WritingRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    # Oturum etkinliğinde görev ve hedef öğe sunucudaki içerikten okunur.
    activity_id: int | None = None
    # Serbest pratikte (etkinlik yok) istemci gönderir.
    task: str | None = Field(default=None, max_length=300)
    target_item_ids: list[int] | None = Field(default=None, min_length=1, max_length=5)


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
    activity = None
    if body.activity_id is not None:
        try:
            activity, content = sessions.owned_activity(db, user.id, body.activity_id)
        except sessions.ActivityNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Etkinlik bulunamadı.") from exc
        if content.kind != "writing":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Yazma etkinliği değil.")
        writing = Writing.model_validate(content.content)
        task, item_ids = writing.task_en, [writing.item_id]
    elif body.task and body.target_item_ids:
        task, item_ids = body.task, body.target_item_ids
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Görev ya da etkinlik gerekli.")

    view = give_feedback(
        db,
        client,
        user_id=user.id,
        task=task,
        target_item_ids=item_ids,
        learner_text=body.text.strip(),
        activity_id=body.activity_id,
    )
    if activity is not None:
        sessions.complete_if_done(db, activity)
    return view


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
