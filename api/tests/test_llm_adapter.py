"""Gerçek SDK'larla adaptörler: yalnızca ağ sahte. Aynı senaryolar iki sağlayıcıda da koşar.

Sahte `LLMClient` bu davranışı gösteremez: `parse` yardımcıları şema dışı yanıtta istisna
fırlatır, adaptörlerin sözleşmesi ise `parsed=None` döndürmektir.
"""

import json
from dataclasses import replace
from typing import Any, Protocol

import anthropic
import httpx2
import openai
import pytest
from pydantic import BaseModel

from app.curriculum.schemas import CurriculumDraft
from app.dialogue.schemas import DialogueTurn
from app.feedback.llm_schema import WritingFeedback
from app.llm.client import AnthropicClient, LLMClient, LLMProviderError, LLMRequest
from app.llm.openai_client import OpenAIClient, strict_schema
from app.llm.pricing import Usage, cost_microusd
from app.llm.purposes import purpose_config
from app.llm.routing import RoutingClient, routing_client
from app.sessions.schemas import SessionOutput

VALID = '{"is_correct": true, "errors": [], "hint_tr": null, "correction": null}'


class Handler(Protocol):
    def __call__(self, request: httpx2.Request) -> httpx2.Response: ...


def _reply(body: dict[str, Any], seen: list[dict[str, Any]] | None = None) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(json.loads(request.content))
        return httpx2.Response(200, json=body)

    return handler


def _http(handler: Handler) -> httpx2.Client:
    return httpx2.Client(transport=httpx2.MockTransport(handler))


def _claude(handler: Handler) -> AnthropicClient:
    adapter = AnthropicClient(api_key="test")
    adapter._client = anthropic.Anthropic(api_key="test", max_retries=0, http_client=_http(handler))
    return adapter


def _gpt(handler: Handler) -> OpenAIClient:
    adapter = OpenAIClient(api_key="test")
    adapter._client = openai.OpenAI(api_key="test", max_retries=0, http_client=_http(handler))
    return adapter


def _claude_body(text: str | None, stop: str) -> dict[str, Any]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": [] if text is None else [{"type": "text", "text": text}],
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 10,
            "cache_creation_input_tokens": 5,
        },
    }


def _gpt_body(text: str | None, stop: str, phase: str | None = None) -> dict[str, Any]:
    """Aynı senaryonun OpenAI biçimi: girdi sayısı önbellekli token'ları da içerir."""
    content: list[dict[str, Any]] = []
    if stop == "refusal":
        if text is not None:
            content = [{"type": "refusal", "refusal": text}]
    elif text is not None:
        content = [{"type": "output_text", "text": text, "annotations": []}]
    status = "incomplete" if stop == "max_tokens" else "completed"
    message: dict[str, Any] = {
        "type": "message",
        "id": "msg_1",
        "role": "assistant",
        "status": status,
        "content": content,
    }
    if phase:
        message["phase"] = phase
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "model": "gpt-6.1-sol-2026-10-01",
        "status": status,
        "incomplete_details": {"reason": "max_output_tokens"} if stop == "max_tokens" else None,
        "output": [{"type": "reasoning", "id": "rs_1", "summary": []}, message],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 115,
            "output_tokens": 50,
            "total_tokens": 165,
            "input_tokens_details": {"cached_tokens": 10, "cache_write_tokens": 5},
            "output_tokens_details": {"reasoning_tokens": 20},
        },
    }


def _request() -> LLMRequest:
    return LLMRequest(purpose_config("feedback"), "static", "özet", "task", WritingFeedback)


def _adapter(provider: str, text: str | None, stop: str) -> LLMClient:
    if provider == "anthropic":
        return _claude(_reply(_claude_body(text, stop)))
    return _gpt(_reply(_gpt_body(text, stop)))


BOTH = pytest.mark.parametrize("provider", ["anthropic", "openai"])


@BOTH
def test_valid_reply_is_parsed(provider: str) -> None:
    result = _adapter(provider, VALID, "end_turn").complete(_request())
    assert isinstance(result.parsed, WritingFeedback)
    assert result.parsed.is_correct is True
    assert result.stop_reason == "end_turn"


@BOTH
def test_usage_means_the_same_for_both_providers(provider: str) -> None:
    """`input_tokens` önbellek dışı girdidir; OpenAI'nin toplamı adaptörde ayrıştırılır."""
    result = _adapter(provider, VALID, "end_turn").complete(_request())
    assert result.usage == Usage(100, 50, 10, 5)


@BOTH
@pytest.mark.parametrize(
    ("text", "stop"),
    [
        ('{"is_correct": tr', "max_tokens"),  # kesilen JSON
        ("I can't help with that.", "refusal"),  # metinli ret
        ('{"unexpected": 1}', "end_turn"),  # şema dışı
        (VALID, "max_tokens"),  # JSON tam olsa da kesilmiş yanıta güvenilmez
    ],
)
def test_failed_replies_return_none_and_keep_the_cost(provider: str, text: str, stop: str) -> None:
    """Çağıran yedek yola geçer; harcanan token kaybolmaz."""
    result = _adapter(provider, text, stop).complete(_request())
    assert result.parsed is None
    assert result.stop_reason == stop
    assert result.raw_text == text
    assert result.usage.output_tokens == 50


@BOTH
def test_empty_refusal_returns_none(provider: str) -> None:
    result = _adapter(provider, None, "refusal").complete(_request())
    assert result.parsed is None and result.raw_text is None


@BOTH
def test_api_errors_become_one_provider_neutral_type(provider: str) -> None:
    def fail(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, json={"error": {"message": "boom"}})

    adapter = _claude(fail) if provider == "anthropic" else _gpt(fail)
    with pytest.raises(LLMProviderError):
        adapter.complete(_request())


def test_claude_request_asks_for_the_schema() -> None:
    seen: list[dict[str, Any]] = []
    _claude(_reply(_claude_body(VALID, "end_turn"), seen)).complete(_request())

    sent = seen[0]
    assert sent["output_config"]["effort"] == "medium"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert sent["fallbacks"] == "default"
    assert "output_format" not in sent


def _openai_request() -> LLMRequest:
    config = replace(purpose_config("feedback"), provider="openai", model="gpt-6.1-sol")
    return LLMRequest(config, "static", "özet", "task", WritingFeedback)


def test_openai_request_shape() -> None:
    seen: list[dict[str, Any]] = []
    _gpt(_reply(_gpt_body(VALID, "end_turn"), seen)).complete(_openai_request())

    sent = seen[0]
    assert sent["store"] is False  # öğrenci metni OpenAI'de saklanmasın
    assert sent["instructions"] == "static"  # önbellek önekten çalışır
    # Tek user mesajı: özet ayrı mesaj olunca öğrenciler önbelleği paylaşamıyor.
    assert sent["input"] == [{"role": "user", "content": "özet\n\ntask"}]
    assert sent["reasoning"] == {"effort": "medium"}
    assert sent["max_output_tokens"] == 2000
    assert sent["text"]["format"]["strict"] is True
    assert sent["text"]["format"]["name"] == "WritingFeedback"
    assert "temperature" not in sent


def test_openai_without_snapshot_sends_only_the_task() -> None:
    seen: list[dict[str, Any]] = []
    request = replace(_openai_request(), snapshot_block=None)
    _gpt(_reply(_gpt_body(VALID, "end_turn"), seen)).complete(request)
    assert seen[0]["input"] == [{"role": "user", "content": "task"}]


def test_openai_ignores_text_outside_the_final_phase() -> None:
    body = _gpt_body("taslak düşünce", "end_turn", phase="commentary")
    final = _gpt_body(VALID, "end_turn", phase="final_answer")["output"][1]
    body["output"].append(final)
    result = _gpt(_reply(body)).complete(_openai_request())
    assert isinstance(result.parsed, WritingFeedback)


def test_openai_cost_uses_the_configured_name_not_the_dated_one() -> None:
    result = _gpt(_reply(_gpt_body(VALID, "end_turn"))).complete(_openai_request())
    assert result.model == "gpt-6.1-sol"
    assert cost_microusd(result.model, result.usage) is not None


@pytest.mark.parametrize("model", [WritingFeedback, SessionOutput, CurriculumDraft, DialogueTurn])
def test_every_output_schema_is_strict(model: type[BaseModel]) -> None:
    """OA-3: tüm alanlar zorunlu, fazladan alan yok, varsayılan değer yok."""

    def check(node: Any) -> None:
        if isinstance(node, dict):
            assert "default" not in node
            assert "allOf" not in node and "not" not in node
            if "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    schema = strict_schema(model)
    assert schema["type"] == "object"
    check(schema)


def test_strict_schema_does_not_touch_the_pydantic_model() -> None:
    strict_schema(WritingFeedback)
    assert "additionalProperties" not in WritingFeedback.model_json_schema()


# --- Yönlendirme ---------------------------------------------------------------


class Recording:
    def __init__(self, label: str) -> None:
        self.label = label
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> Any:
        self.requests.append(request)
        return self.label


def test_request_goes_to_the_configured_provider() -> None:
    claude, gpt = Recording("claude"), Recording("gpt")
    router = RoutingClient({"anthropic": lambda: claude, "openai": lambda: gpt})

    assert router.complete(_request()) == "claude"
    assert router.complete(_openai_request()) == "gpt"


def test_adapter_is_built_once_and_only_when_needed() -> None:
    built: list[str] = []

    def factory() -> LLMClient:
        built.append("gpt")
        return Recording("gpt")

    router = RoutingClient({"anthropic": lambda: Recording("c"), "openai": factory})
    router.complete(_request())
    assert built == []
    router.complete(_openai_request())
    router.complete(_openai_request())
    assert built == ["gpt"]


def test_missing_key_fails_like_a_provider_error() -> None:
    """Çağıran yedek yola geçer; uygulama anahtarsız da açılır."""
    with pytest.raises(LLMProviderError):
        routing_client("test", None).complete(_openai_request())


def test_purposes_can_be_split_between_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider_generation", "openai")
    session, feedback = purpose_config("session"), purpose_config("feedback")

    assert (session.provider, session.model) == ("openai", settings.openai_model_generation)
    assert session.server_fallback is False
    assert (feedback.provider, feedback.model) == ("anthropic", "claude-sonnet-5-5")
    assert feedback.server_fallback is True


def test_claude_stays_the_default_until_oa5() -> None:
    for purpose in ("session", "extra", "feedback", "dialogue", "curriculum"):
        assert purpose_config(purpose).provider == "anthropic"  # type: ignore[arg-type]
