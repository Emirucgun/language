"""Bugünün oturumu, cevaplar ve (geçici) serbest yazma pratiği."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth.models import User
from app.content.models import Item
from app.deps import ConsentedUser, Db, get_llm_client
from app.llm.client import LLMClient
from app.scheduler.service import select_items
from app.sessions import service
from app.sessions.generation import ensure_session
from app.sessions.schemas import AnswerRequest, AnswerResult, SessionView

router = APIRouter(tags=["session"])


def local_today(user: User) -> date:
    return datetime.now(ZoneInfo(user.timezone)).date()


@router.get("/api/session/today")
def today(
    db: Db, user: ConsentedUser, client: Annotated[LLMClient, Depends(get_llm_client)]
) -> SessionView:
    """Gece işi gelene kadar oturum ilk istekte üretilir (birkaç saniye sürebilir)."""
    study = ensure_session(db, client, user, local_today(user))
    return service.session_view(db, study)


@router.post("/api/activities/{activity_id}/answer")
def post_answer(activity_id: int, body: AnswerRequest, db: Db, user: ConsentedUser) -> AnswerResult:
    try:
        return service.answer(db, user.id, activity_id, body)
    except service.ActivityNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Etkinlik bulunamadı.") from exc
    except service.AlreadyAnswered as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu soru zaten cevaplandı.") from exc


# --- Serbest yazma pratiği (ek çalışma) -------------------------------------
# GEÇİCİ: ek çalışma etkinlikleri talep anında üretilene kadar sabit bir görev cümlesi.


class WritingTask(BaseModel):
    task: str  # modele giden görev (İngilizce)
    task_tr: str  # öğrenciye gösterilen yönerge
    target_item_ids: list[int]
    item_en: str
    item_tr: str


@router.get("/api/practice/writing-task", tags=["practice"])
def writing_task(db: Db, user: ConsentedUser) -> WritingTask:
    active = select(Item.id).where(Item.active, Item.cefr.in_(("A1", "A2")))
    candidates = list(db.scalars(active.order_by(Item.sublevel.nulls_last(), Item.id)))
    if not candidates:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Henüz içerik yüklenmedi.")

    # Önce vadesi gelen tekrar, yoksa sıradaki yeni öğe; ikisi de yoksa rastgele bir öğe.
    selection = select_items(
        db,
        user.id,
        due_before=datetime.now(UTC) + timedelta(hours=1),
        candidate_new_ids=candidates,
        max_reviews=1,
        max_new=1,
    )
    chosen = selection.review_item_ids or selection.new_item_ids
    picked = chosen[0] if chosen else db.scalar(active.order_by(func.random()).limit(1))
    item = db.get_one(Item, picked)
    return WritingTask(
        task=f'Write one sentence about yourself using "{item.text_en}".',
        task_tr=f"“{item.text_en}” ({item.text_tr}) kullanarak kendinle ilgili bir cümle yaz.",
        target_item_ids=[item.id],
        item_en=item.text_en,
        item_tr=item.text_tr,
    )
