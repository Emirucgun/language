"""Amaç (purpose) başına model ve çıktı ayarları; model bir ayardır (docs/architecture/llm.md)."""

from dataclasses import dataclass
from typing import Literal

from app.config import settings

Purpose = Literal["session", "extra", "feedback", "dialogue", "curriculum"]
Effort = Literal["low", "medium", "high"]
Provider = Literal["anthropic", "openai"]


@dataclass(frozen=True, slots=True)
class PurposeConfig:
    model: str
    max_tokens: int  # düşünme token'ları da bu sınıra dahil
    effort: Effort
    # Reddedilen isteği sunucu tarafında başka modelle yeniden dener (yalnızca Sonnet 5.5).
    server_fallback: bool
    provider: Provider = "anthropic"


def _config(
    provider: Provider, models: tuple[str, str], max_tokens: int, effort: Effort, fallback: bool
) -> PurposeConfig:
    """`models`: (Claude, OpenAI). Sunucu tarafı yedek yalnızca Claude'da var."""
    claude, gpt = models
    if provider == "openai":
        return PurposeConfig(gpt, max_tokens, effort, False, provider)
    return PurposeConfig(claude, max_tokens, effort, fallback, provider)


def purpose_config(purpose: Purpose) -> PurposeConfig:
    generation = (settings.llm_model_generation, settings.openai_model_generation)
    feedback = (settings.llm_model_feedback, settings.openai_model_feedback)
    curriculum = (settings.llm_model_curriculum, settings.openai_model_curriculum)
    to_generation = settings.llm_provider_generation
    to_feedback = settings.llm_provider_feedback
    configs: dict[Purpose, PurposeConfig] = {
        "session": _config(to_generation, generation, 8000, "low", False),
        "extra": _config(to_generation, generation, 4000, "low", False),
        "feedback": _config(to_feedback, feedback, 2000, "medium", True),
        "dialogue": _config(to_feedback, feedback, 1500, "low", True),
        "curriculum": _config(settings.llm_provider_curriculum, curriculum, 8000, "medium", True),
    }
    return configs[purpose]
