"""Ses modellerinin fiyatı (mikro-dolar). Kaynak: OpenAI liste fiyatı, 4 Kas 2026."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Usage:
    text_input_tokens: int = 0
    text_output_tokens: int = 0
    audio_output_tokens: int = 0


@dataclass(frozen=True, slots=True)
class Price:
    text_input_per_mtok: float
    text_output_per_mtok: float
    audio_output_per_mtok: float


PRICES: dict[str, Price] = {
    "gpt-realtime-2.1-mini": Price(0.60, 2.40, 20.00),
}
TRANSCRIBE_PER_MINUTE: dict[str, float] = {"gpt-transcribe": 0.0045}


def cost_microusd(model: str, usage: Usage) -> int | None:
    """Bilinmeyen modelde None. Mtok başına dolar = token başına mikro-dolar."""
    price = PRICES.get(model)
    if price is None:
        return None
    return round(
        usage.text_input_tokens * price.text_input_per_mtok
        + usage.text_output_tokens * price.text_output_per_mtok
        + usage.audio_output_tokens * price.audio_output_per_mtok
    )
