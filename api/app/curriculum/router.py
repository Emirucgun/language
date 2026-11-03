from typing import Annotated

from fastapi import APIRouter, Depends

from app.curriculum.schemas import CurriculumView
from app.curriculum.service import ensure_curriculum, view
from app.deps import ConsentedUser, Db, get_llm_client
from app.llm.client import LLMClient

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


@router.get("")
def get_curriculum(
    db: Db, user: ConsentedUser, client: Annotated[LLMClient, Depends(get_llm_client)]
) -> CurriculumView:
    """Güncel müfredat; yoksa ilk istekte oluşturulur (birkaç saniye sürebilir)."""
    return view(db, ensure_curriculum(db, client, user))
