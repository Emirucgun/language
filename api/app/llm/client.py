"""Sağlayıcı soyutlaması. Uygulamanın geri kalanı yalnızca `LLMClient` arayüzünü görür.

İstek üç katmanlıdır (Technical MVP, 6.2):
  1. statik blok   – amaç başına herkes için aynı, 1 saatlik önbellek
  2. öğrenci özeti – kullanıcı başına günde bir donar, 5 dakikalık önbellek
  3. görev         – her çağrıda değişir, önbelleğe alınmaz
"""

import time
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel, ValidationError

from app.llm.pricing import Usage
from app.llm.purposes import PurposeConfig

FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True, slots=True)
class LLMRequest:
    config: PurposeConfig
    static_block: str
    snapshot_block: str | None
    task: str
    output_type: type[BaseModel]


@dataclass(frozen=True, slots=True)
class LLMResult:
    model: str
    parsed: BaseModel | None  # şema tutmazsa, ret ya da kesilme olursa None
    usage: Usage
    stop_reason: str | None
    latency_ms: int
    raw_text: str | None


class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> LLMResult:
        """Yanıt geldiyse istisna fırlatmaz: ret, kesilme ve şema dışı çıktı `parsed=None`
        döner, token kullanımı korunur. Yalnızca API ve ağ hataları istisnadır."""
        ...


def build_system(request: LLMRequest) -> list[dict[str, Any]]:
    """Önbellek kırılma noktaları: 1 saatlik giriş 5 dakikalıktan önce gelmek zorunda."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": request.static_block,
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        }
    ]
    if request.snapshot_block:
        blocks.append(
            {
                "type": "text",
                "text": request.snapshot_block,
                "cache_control": {"type": "ephemeral"},
            }
        )
    return blocks


def parse_output(request: LLMRequest, raw_text: str | None, complete: bool) -> BaseModel | None:
    """Yalnızca sorunsuz biten yanıt kabul edilir; kesilmiş JSON tam görünse de güvenilmez."""
    if not complete or raw_text is None:
        return None
    try:
        return request.output_type.model_validate_json(raw_text)
    except ValidationError:
        return None


class AnthropicClient:
    def __init__(self, api_key: str | None = None, timeout_s: float = 60.0) -> None:
        # SDK geçici hataları (429, 5xx, bağlantı) kendisi 2 kez yeniden dener.
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=2)

    def complete(self, request: LLMRequest) -> LLMResult:
        config = request.config
        extra: dict[str, Any] = {}
        if config.server_fallback:
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}

        # `parse` değil `create`: `parse` şema dışı yanıtta istisna fırlatır ve kullanım
        # bilgisini kaybettirir. Doğrulama `parse_output`ta.
        schema = anthropic.transform_schema(request.output_type.model_json_schema())
        create: Any = self._client.beta.messages.create  # aşırı yüklemeler **extra ile uyuşmaz
        started = time.monotonic()
        response: BetaMessage = create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=build_system(request),
            messages=[{"role": "user", "content": request.task}],
            output_config={
                "effort": config.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            **extra,
        )
        latency_ms = round((time.monotonic() - started) * 1000)

        usage = response.usage
        raw_text = next((b.text for b in response.content if b.type == "text"), None)
        return LLMResult(
            model=response.model,
            parsed=parse_output(request, raw_text, response.stop_reason == "end_turn"),
            usage=Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_input_tokens or 0,
                cache_write_tokens=usage.cache_creation_input_tokens or 0,
            ),
            stop_reason=response.stop_reason,
            latency_ms=latency_ms,
            raw_text=raw_text,
        )
