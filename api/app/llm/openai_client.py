"""OpenAI adaptörü (Responses API).

`responses.parse` değil `create`: `parse` şema dışı yanıtta istisna fırlatır ve kullanım
bilgisini kaybettirir; doğrulama `parse_output`ta, Claude adaptörüyle aynı sözleşmeyle.

Yanıtlar OpenAI'de saklanmasın diye `store=False`: öğrenci metni taşırlar.
"""

import copy
import time
from typing import Any

import openai
from openai.types.responses import Response
from pydantic import BaseModel

from app.llm.client import LLMProviderError, LLMRequest, LLMResult, parse_output
from app.llm.pricing import Usage

FINAL_PHASE = "final_answer"
# Sağlayıcıdan bağımsız durma sebepleri (bkz. docs/architecture/llm.md).
INCOMPLETE_REASONS = {"max_output_tokens": "max_tokens"}


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Strict mod: her nesnede tüm alanlar zorunlu ve fazladan alan yok.

    İsteğe bağlı alan `null` birliğiyle ifade edilir; varsayılan değer kullanılmaz.
    """
    schema = copy.deepcopy(model.model_json_schema())

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def _input(request: LLMRequest) -> list[dict[str, str]]:
    """Tek `user` mesajı, özet başta. Özet ayrı `developer` mesajı olunca farklı öğrenciler
    statik bloğu paylaşamıyor, önbellek okuması sıfıra düşüyordu (ölçüldü: 5 Kas 2026)."""
    parts = [request.snapshot_block, request.task] if request.snapshot_block else [request.task]
    return [{"role": "user", "content": "\n\n".join(parts)}]


def _final_parts(response: Response) -> tuple[str | None, str | None]:
    """(metin, ret metni). Yalnızca nihai cevap fazı sonuçtur."""
    text: str | None = None
    refusal: str | None = None
    for item in response.output:
        if item.type != "message" or getattr(item, "phase", None) not in (None, FINAL_PHASE):
            continue
        for part in item.content:
            if part.type == "refusal":
                refusal = part.refusal
            elif part.type == "output_text":
                text = part.text
    return text, refusal


def _stop_reason(response: Response, refusal: str | None) -> str | None:
    if refusal is not None:
        return "refusal"
    if response.status == "completed":
        return "end_turn"
    if response.status == "incomplete" and response.incomplete_details is not None:
        reason = response.incomplete_details.reason or "incomplete"
        return INCOMPLETE_REASONS.get(reason, reason)
    return response.status


def _usage(response: Response) -> Usage:
    """`input_tokens` önbellekli token'ları da içerir; `Usage.input_tokens` içermez."""
    usage = response.usage
    if usage is None:
        return Usage(0, 0)
    details = usage.input_tokens_details
    cached = details.cached_tokens or 0
    written = details.cache_write_tokens or 0
    return Usage(
        input_tokens=max(0, usage.input_tokens - cached - written),
        output_tokens=usage.output_tokens,
        cache_read_tokens=cached,
        cache_write_tokens=written,
    )


class OpenAIClient:
    def __init__(self, api_key: str | None = None, timeout_s: float = 60.0) -> None:
        # SDK geçici hataları (429, 5xx, bağlantı) kendisi 2 kez yeniden dener.
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout_s, max_retries=2)

    def complete(self, request: LLMRequest) -> LLMResult:
        config = request.config
        create: Any = self._client.responses.create  # aşırı yüklemeler dict girdiyle uyuşmaz
        started = time.monotonic()
        try:
            response: Response = create(
                model=config.model,
                instructions=request.static_block,
                input=_input(request),
                max_output_tokens=config.max_tokens,
                reasoning={"effort": config.effort},
                text={
                    "format": {
                        "type": "json_schema",
                        "name": request.output_type.__name__,
                        "schema": strict_schema(request.output_type),
                        "strict": True,
                    }
                },
                store=False,
            )
        except openai.OpenAIError as exc:
            raise LLMProviderError(f"{type(exc).__name__}: {exc}") from exc
        latency_ms = round((time.monotonic() - started) * 1000)

        text, refusal = _final_parts(response)
        stop_reason = _stop_reason(response, refusal)
        return LLMResult(
            # Yanıttaki ad tarihli olabilir; fiyat tablosu ayardaki adı bilir.
            model=config.model,
            parsed=parse_output(request, text, stop_reason == "end_turn"),
            usage=_usage(response),
            stop_reason=stop_reason,
            latency_ms=latency_ms,
            raw_text=text if text is not None else refusal,
        )
