"""Pratik uç noktaları.

GEÇİCİ: Etkinlik üretimi yazılana kadar yazma pratiği, tekrar motorunun seçtiği bir
öğe için sabit bir görev cümlesiyle sunulur. Etkinlik üretimi gelince bu uç nokta
`activity_contents`'ten gelen gerçek etkinliği döndürecek.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.content.models import Item
from app.deps import ConsentedUser, Db
from app.scheduler.service import select_items


class WritingTask(BaseModel):
    task: str  # modele giden görev (İngilizce)
    task_tr: str  # öğrenciye gösterilen yönerge
    target_item_ids: list[int]
    item_en: str
    item_tr: str


router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/writing-task")
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
