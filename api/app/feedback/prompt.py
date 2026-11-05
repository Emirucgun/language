"""Yazma geri bildirimi için prompt parçaları."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.models import ErrorTag
from app.llm.prompts import quote_learner, render_static

PROMPT_VERSION = "v3"  # v3: öğrenci metni sınırlayıcı içinde veri; enjeksiyona karşı


def free_writing_task(item_text: str) -> str:
    """Serbest yazma görevi: yalnızca sunucuda kurulur, istemciden görev metni alınmaz."""
    return f'Write one sentence about yourself using "{item_text}".'


def error_catalog(session: Session) -> str:
    """Katalog satırları koda göre sıralı: aynı katalog her zaman aynı metni üretir."""
    tags = session.scalars(
        select(ErrorTag).where(ErrorTag.active, ErrorTag.code != "OTHER").order_by(ErrorTag.code)
    ).all()
    return "\n".join(f"- {t.code}: {t.name_tr}" for t in tags)


def static_block(session: Session) -> str:
    return render_static("feedback", PROMPT_VERSION, {"ERROR_CATALOG": error_catalog(session)})


def task_block(
    *, task: str, target_items: Sequence[str], learner_text: str, recent_codes: Sequence[str]
) -> str:
    """Yalnızca bu görevin girdisi; geçmiş konuşma ya da kimlik bilgisi yok."""
    lines = [
        f"Task: {task}",
        f"Target item(s): {', '.join(repr(i) for i in target_items)}",
    ]
    if recent_codes:
        lines.append(f"Recent errors on these items: {', '.join(recent_codes)}")
    lines.append(f"Learner: {quote_learner(learner_text)}")
    return "\n".join(lines)
