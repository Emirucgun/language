"""Yazılı diyalog uç noktaları (ek çalışma)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import ConsentedUser, Db, get_llm_client
from app.dialogue import service
from app.dialogue.schemas import DialogueView, ReplyRequest
from app.llm.client import LLMClient

router = APIRouter(prefix="/api/practice/dialogue", tags=["practice"])


def _load(db: Db, user: ConsentedUser, activity_id: int) -> service.Dialogue:
    try:
        return service.load(db, user.id, activity_id)
    except service.DialogueNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diyalog bulunamadı.") from exc


@router.post("")
def start(db: Db, user: ConsentedUser) -> DialogueView:
    """Senaryo ve açılış cümlesi sabit: LLM çağrısı yok, anında döner."""
    return service.view(db, _load(db, user, service.start(db, user)))


@router.get("/{activity_id}")
def get_dialogue(activity_id: int, db: Db, user: ConsentedUser) -> DialogueView:
    return service.view(db, _load(db, user, activity_id))


@router.post("/{activity_id}/reply")
def post_reply(
    activity_id: int,
    body: ReplyRequest,
    db: Db,
    user: ConsentedUser,
    client: Annotated[LLMClient, Depends(get_llm_client)],
) -> DialogueView:
    """Bir öğrenci cümlesi → geri bildirim + partnerin cevabı (birkaç saniye). Tüm görünüm döner."""
    dialogue = _load(db, user, activity_id)
    try:
        service.reply(db, client, dialogue, body.text.strip())
    except service.DialogueFinished as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu diyalog bitti.") from exc
    return service.view(db, dialogue)
