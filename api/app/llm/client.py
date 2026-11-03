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
from pydantic import BaseModel

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
    def complete(self, request: LLMRequest) -> LLMResult: ...


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


class AnthropicClient:
    def __init__(self, api_key: str | None = None, timeout_s: float = 60.0) -> None:
        # SDK geçici hataları (429, 5xx, bağlantı) kendisi 2 kez yeniden dener.
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=2)

    def complete(self, request: LLMRequest) -> LLMResult:
        config = request.config
        extra: dict[str, Any] = {}
        if config.server_fallback:
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}

        started = time.monotonic()
        response = self._client.beta.messages.parse(
            model=config.model,
            max_tokens=config.max_tokens,
            system=build_system(request),  # type: ignore[arg-type]
            messages=[{"role": "user", "content": request.task}],
            output_format=request.output_type,
            output_config={"effort": config.effort},
            **extra,
        )
        latency_ms = round((time.monotonic() - started) * 1000)

        usage = response.usage
        raw_text = next((b.text for b in response.content if b.type == "text"), None)
        parsed = response.parsed_output if response.stop_reason == "end_turn" else None
        return LLMResult(
            model=response.model,
            parsed=parsed,
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
