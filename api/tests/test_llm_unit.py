from typing import Any

import pytest
from pydantic import BaseModel

from app.feedback.llm_schema import WritingFeedback
from app.llm.client import LLMRequest, build_system
from app.llm.pricing import Usage, cost_microusd
from app.llm.prompts import estimate_tokens, render_static
from app.llm.purposes import purpose_config
from app.llm.snapshot import LearnerFacts, render

CATALOG = "\n".join(
    f"- {code}: {name}"
    for code, name in [
        ("ARTICLE", "Artikel eksik ya da fazla"),
        ("BE_VERB", "Be fiili eksik ya da yanlış"),
        ("PLURAL", "Çoğul eki"),
        ("PREPOSITION", "Edat seçimi"),
        ("SUBJECT", "Özne eksik"),
        ("TENSE", "Zaman uyumsuzluğu"),
        ("WORD_ORDER", "Kelime sırası"),
    ]
)


def test_cost_uses_cache_multipliers() -> None:
    usage = Usage(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    # Sonnet 5.5: 2 + 10 + 0.2 (okuma) + 4 (1 saatlik yazma) dolar
    assert cost_microusd("claude-sonnet-5-5", usage) == 16_200_000
    assert cost_microusd("unknown-model", usage) is None


def test_static_block_comes_first_with_longer_ttl() -> None:
    request = LLMRequest(
        config=purpose_config("feedback"),
        static_block="static",
        snapshot_block="snapshot",
        task="task",
        output_type=BaseModel,
    )
    static, snapshot = build_system(request)
    assert static["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert snapshot["cache_control"] == {"type": "ephemeral"}


def test_feedback_static_block_is_cacheable_and_stable() -> None:
    first = render_static("feedback", "v1", {"ERROR_CATALOG": CATALOG})
    second = render_static("feedback", "v1", {"ERROR_CATALOG": CATALOG})
    assert first == second
    assert "{{" not in first
    # Haiku/Sonnet 5.5'te önbelleğe alınabilir en kısa önek 512 token.
    assert estimate_tokens(first) >= 600


def test_missing_placeholder_is_an_error() -> None:
    with pytest.raises(KeyError):
        render_static("feedback", "v1")


def test_snapshot_is_short_and_deterministic() -> None:
    facts = LearnerFacts(
        level="A1",
        goal="travel",
        daily_minutes=15,
        interests=tuple(f"interest{i}" for i in range(20)),
        weak_skills=("listening", "writing"),
        frequent_errors=(("ARTICLE", 5), ("BE_VERB", 3), ("TENSE", 2), ("PLURAL", 1)),
        learned_items=42,
    )
    text = render(facts)
    assert text == render(facts)
    assert estimate_tokens(text) <= 300
    assert "PLURAL" not in text  # en sık 3 hata
    assert text.count("interest") == 5


def test_anthropic_request_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gerçek API'ye gitmeden SDK'ya verilen parametreleri doğrular."""
    from app.llm.client import FALLBACK_BETA, AnthropicClient

    captured: dict[str, Any] = {}

    def fake_parse(**kwargs: Any) -> Any:
        captured.update(kwargs)
        raise RuntimeError("stop")

    client = AnthropicClient(api_key="test")
    monkeypatch.setattr(client._client.beta.messages, "parse", fake_parse)
    request = LLMRequest(
        config=purpose_config("feedback"),
        static_block="static",
        snapshot_block=None,
        task="task",
        output_type=WritingFeedback,
    )
    with pytest.raises(RuntimeError):
        client.complete(request)

    assert captured["model"] == "claude-sonnet-5-5"
    assert captured["output_format"] is WritingFeedback
    assert captured["output_config"] == {"effort": "medium"}
    assert captured["betas"] == [FALLBACK_BETA] and captured["fallbacks"] == "default"
    assert "temperature" not in captured  # güncel API bunu reddediyor
    assert len(captured["system"]) == 1  # özet yoksa ikinci blok yok

    # Haiku rotasında sunucu tarafı yedek yok.
    captured.clear()
    with pytest.raises(RuntimeError):
        client.complete(LLMRequest(purpose_config("session"), "s", None, "t", WritingFeedback))
    assert captured["model"] == "claude-haiku-5-5" and "fallbacks" not in captured


def test_feedback_schema_accepts_correct_sentence() -> None:
    parsed = WritingFeedback.model_validate(
        {"is_correct": True, "errors": [], "hint_tr": None, "correction": None}
    )
    assert parsed.is_correct
