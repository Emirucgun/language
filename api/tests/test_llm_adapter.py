"""Gerçek SDK ile adaptör: yalnızca ağ sahte. Sahte `LLMClient` bu davranışı gösteremez."""

import json
from typing import Any

import anthropic
import httpx2
import pytest

from app.feedback.llm_schema import WritingFeedback
from app.llm.client import AnthropicClient, LLMRequest
from app.llm.purposes import purpose_config

VALID = '{"is_correct": true, "errors": [], "hint_tr": null, "correction": null}'


def _message(content: list[dict[str, Any]], stop_reason: str) -> dict[str, Any]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 10,
            "cache_creation_input_tokens": 5,
        },
    }


def _adapter(body: dict[str, Any], seen: list[dict[str, Any]] | None = None) -> AnthropicClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(json.loads(request.content))
        return httpx2.Response(200, json=body)

    adapter = AnthropicClient(api_key="test")
    adapter._client = anthropic.Anthropic(
        api_key="test",
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    return adapter


def _request() -> LLMRequest:
    return LLMRequest(purpose_config("feedback"), "static", None, "task", WritingFeedback)


def test_valid_reply_is_parsed() -> None:
    body = _message([{"type": "text", "text": VALID}], "end_turn")
    result = _adapter(body).complete(_request())
    assert isinstance(result.parsed, WritingFeedback)
    assert result.parsed.is_correct is True
    assert (result.usage.input_tokens, result.usage.output_tokens) == (100, 50)
    assert (result.usage.cache_read_tokens, result.usage.cache_write_tokens) == (10, 5)


@pytest.mark.parametrize(
    ("text", "stop_reason"),
    [
        ('{"is_correct": tr', "max_tokens"),  # kesilen JSON
        ("I can't help with that.", "refusal"),  # metinli ret
        ('{"unexpected": 1}', "end_turn"),  # şema dışı
        (VALID, "max_tokens"),  # JSON tam olsa da kesilmiş yanıta güvenilmez
    ],
)
def test_failed_replies_return_none_and_keep_the_cost(text: str, stop_reason: str) -> None:
    """Çağıran yedek yola geçer; harcanan token kaybolmaz."""
    body = _message([{"type": "text", "text": text}], stop_reason)
    result = _adapter(body).complete(_request())
    assert result.parsed is None
    assert result.stop_reason == stop_reason
    assert result.raw_text == text
    assert result.usage.output_tokens == 50


def test_empty_refusal_returns_none() -> None:
    result = _adapter(_message([], "refusal")).complete(_request())
    assert result.parsed is None and result.raw_text is None


def test_request_body_asks_for_the_schema() -> None:
    seen: list[dict[str, Any]] = []
    body = _message([{"type": "text", "text": VALID}], "end_turn")
    _adapter(body, seen).complete(_request())

    sent = seen[0]
    assert sent["output_config"]["effort"] == "medium"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert sent["fallbacks"] == "default"
    assert "output_format" not in sent
