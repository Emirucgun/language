"""Amaç (purpose) başına model ve çıktı ayarları; model bir ayardır (Technical MVP, 6.1)."""

from dataclasses import dataclass
from typing import Literal

from app.config import settings

Purpose = Literal["session", "extra", "feedback", "dialogue", "curriculum"]
Effort = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class PurposeConfig:
    model: str
    max_tokens: int  # düşünme token'ları da bu sınıra dahil
    effort: Effort
    # Reddedilen isteği sunucu tarafında başka modelle yeniden dener (yalnızca Sonnet 5.5).
    server_fallback: bool


def purpose_config(purpose: Purpose) -> PurposeConfig:
    generation = settings.llm_model_generation
    feedback = settings.llm_model_feedback
    curriculum = settings.llm_model_curriculum
    configs: dict[Purpose, PurposeConfig] = {
        "session": PurposeConfig(generation, 8000, "low", False),
        "extra": PurposeConfig(generation, 4000, "low", False),
        "feedback": PurposeConfig(feedback, 2000, "medium", True),
        "dialogue": PurposeConfig(feedback, 1500, "low", True),
        "curriculum": PurposeConfig(curriculum, 8000, "medium", True),
    }
    return configs[purpose]
