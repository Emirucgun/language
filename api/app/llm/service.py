"""LLM'e giden tek kapı: limit, kişisel veri koruması, çağrı ve `llm_calls` kaydı.

Başarısız çağrı (ret, kesilme, şema dışı çıktı, API hatası) istisna fırlatmaz; sonuç
`None` döner ve çağıran yedek yola geçer ("şimdilik atladık" ya da şablon). Yalnızca
günlük limit ve kişisel veri ihlali istisnadır: bunlar programlama ya da politika hatasıdır.
"""

import re
import uuid
from dataclasses import dataclass

import anthropic
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.llm.client import LLMClient, LLMRequest
from app.llm.models import LlmCall
from app.llm.pricing import cost_microusd
from app.llm.purposes import Purpose, purpose_config

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class DailyLimitExceeded(Exception):
    pass


class PersonalDataInPrompt(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Prompt:
    purpose: Purpose
    prompt_version: str
    static_block: str
    task: str
    snapshot_id: int | None = None
    snapshot_block: str | None = None


def calls_today(session: Session, user_id: uuid.UUID) -> int:
    """Kullanıcının kendi saat dilimindeki bugünkü çağrı sayısı."""
    day_start = text(
        "date_trunc('day', now() AT TIME ZONE "
        "(SELECT timezone FROM learning.users WHERE id = :uid)) AT TIME ZONE "
        "(SELECT timezone FROM learning.users WHERE id = :uid)"
    ).bindparams(uid=user_id)
    return (
        session.scalar(
            select(func.count())
            .select_from(LlmCall)
            .where(LlmCall.user_id == user_id, LlmCall.created_at >= day_start)
        )
        or 0
    )


def _guard_personal_data(prompt: Prompt) -> None:
    for part in (prompt.static_block, prompt.snapshot_block or "", prompt.task):
        if EMAIL.search(part):
            raise PersonalDataInPrompt("Prompt e-posta adresi içeriyor; LLM'e kimlik gönderilmez.")


def generate_structured[T: BaseModel](
    session: Session,
    client: LLMClient,
    *,
    prompt: Prompt,
    output_type: type[T],
    user_id: uuid.UUID | None,
) -> tuple[T | None, LlmCall]:
    """Çağrıyı yapar ve kaydeder. `LlmCall` satırı eklenir; commit çağırana aittir."""
    _guard_personal_data(prompt)
    if user_id is not None and calls_today(session, user_id) >= (
        settings.llm_daily_call_limit_per_user
    ):
        raise DailyLimitExceeded(str(user_id))

    config = purpose_config(prompt.purpose)
    call = LlmCall(
        user_id=user_id,
        purpose=prompt.purpose,
        model=config.model,
        prompt_version=prompt.prompt_version,
        snapshot_id=prompt.snapshot_id,
    )
    parsed: T | None = None
    try:
        result = client.complete(
            LLMRequest(
                config=config,
                static_block=prompt.static_block,
                snapshot_block=prompt.snapshot_block,
                task=prompt.task,
                output_type=output_type,
            )
        )
    except anthropic.APIError as exc:
        call.status = "error"
        call.raw_on_failure = f"{type(exc).__name__}: {exc}"[:2000]
    else:
        call.model = result.model
        call.input_tokens = result.usage.input_tokens
        call.output_tokens = result.usage.output_tokens
        call.cache_read_tokens = result.usage.cache_read_tokens
        call.cache_write_tokens = result.usage.cache_write_tokens
        call.latency_ms = result.latency_ms
        call.stop_reason = result.stop_reason
        call.cost_microusd = cost_microusd(result.model, result.usage)
        if isinstance(result.parsed, output_type):
            call.status = "ok"
            parsed = result.parsed
        else:
            # Ham yanıt yalnızca hata durumunda saklanır (30 gün sonra temizlenir).
            call.status = "refused" if result.stop_reason == "refusal" else "invalid"
            call.raw_on_failure = result.raw_text

    session.add(call)
    session.flush()
    return parsed, call
