"""Bugünün oturumu, cevaplar ve ek çalışma (tekrar, okuma, yazma)."""

import random
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.models import User
from app.content.models import Item
from app.curriculum.service import latest, new_item_order, pool_for
from app.deps import ConsentedUser, Db, get_llm_client
from app.llm.client import LLMClient
from app.onboarding.fixed_tests import user_level
from app.scheduler.service import select_items
from app.sessions import extra, service
from app.sessions.extra import ExtraKind
from app.sessions.generation import ensure_session
from app.sessions.schemas import ActivityView, AnswerRequest, AnswerResult, SessionView

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


# --- Ek çalışma -------------------------------------------------------------


class Recommendation(BaseModel):
    recommended: ExtraKind


class ExtraRequest(BaseModel):
    kind: Literal["recall", "reading"]


class ExtraView(BaseModel):
    kind: str
    activities: list[ActivityView]


@router.get("/api/practice/recommendation", tags=["practice"])
def get_recommendation(db: Db, user: ConsentedUser) -> Recommendation:
    return Recommendation(recommended=extra.recommend(db, user))


@router.post("/api/practice/extra", tags=["practice"])
def post_extra(
    body: ExtraRequest,
    db: Db,
    user: ConsentedUser,
    client: Annotated[LLMClient, Depends(get_llm_client)],
) -> ExtraView:
    """Seçildiği anda üretilir (birkaç saniye). Okuma üretilemezse etkinlik listesi boş döner."""
    try:
        ids = extra.generate_extra(db, client, user, body.kind)
    except extra.NothingToPractise as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ek çalışma için önce bugünün oturumunu yap."
        ) from exc
    views = [service.activity_view(db, *service.owned_activity(db, user.id, i)) for i in ids]
    return ExtraView(kind=body.kind, activities=views)


# --- Serbest yazma (ek çalışma) ----------------------------------------------
# Yazma görevi tek cümle olduğu için LLM'siz şablon; öğe tekrar motorundan gelir.


class WritingTask(BaseModel):
    task_tr: str  # öğrenciye gösterilen yönerge; modele giden görev sunucuda kurulur
    target_item_ids: list[int]
    item_en: str
    item_tr: str


@router.get("/api/practice/writing-task", tags=["practice"])
def writing_task(db: Db, user: ConsentedUser) -> WritingTask:
    start_level, _ = user_level(db, user.id)
    pool = [p.id for p in pool_for(db, start_level)]
    if not pool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Henüz içerik yüklenmedi.")
    # Oturumla aynı kaynak: müfredat sırası (havuzdan çıkmış öğeler atlanır); plan yoksa havuz.
    curriculum = latest(db, user.id)
    active = set(pool)
    planned = [i for i in new_item_order(curriculum) if i in active] if curriculum else []
    candidates = planned or pool

    # Önce vadesi gelen tekrar, yoksa sıradaki yeni öğe; ikisi de yoksa plandan rastgele bir öğe.
    selection = select_items(
        db,
        user.id,
        due_before=datetime.now(UTC) + timedelta(hours=1),
        candidate_new_ids=candidates,
        max_reviews=1,
        max_new=1,
    )
    chosen = selection.review_item_ids or selection.new_item_ids
    picked = chosen[0] if chosen else random.choice(candidates)
    item = db.get_one(Item, picked)
    return WritingTask(
        task_tr=f"“{item.text_en}” ({item.text_tr}) kullanarak kendinle ilgili bir cümle yaz.",
        target_item_ids=[item.id],
        item_en=item.text_en,
        item_tr=item.text_tr,
    )
