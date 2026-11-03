"""Model fiyatları ve çağrı maliyeti (mikro-dolar). Kaynak: Anthropic liste fiyatı, Kas 2026.

Önbellek: 1 saatlik yazma girdi fiyatının 2 katı, 5 dakikalık yazma 1.25 katı, okuma 0.1 katı.
Statik bloklar 1 saatlik önbelleğe yazılır; hesap bu yüzden tutucu olarak 2 katı kullanır.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Price:
    input_per_mtok: float
    output_per_mtok: float

    @property
    def cache_read_per_mtok(self) -> float:
        return self.input_per_mtok * 0.1

    @property
    def cache_write_per_mtok(self) -> float:
        return self.input_per_mtok * 2


PRICES: dict[str, Price] = {
    "claude-haiku-5-5": Price(0.10, 0.50),
    "claude-sonnet-5-5": Price(2.00, 10.00),
    "claude-opus-5-5": Price(4.00, 20.00),
}


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


def cost_microusd(model: str, usage: Usage) -> int | None:
    """Bilinmeyen modelde None: fiyat tablosu güncellenene kadar maliyet boş kalır."""
    price = PRICES.get(model)
    if price is None:
        return None
    dollars = (
        usage.input_tokens * price.input_per_mtok
        + usage.output_tokens * price.output_per_mtok
        + usage.cache_read_tokens * price.cache_read_per_mtok
        + usage.cache_write_tokens * price.cache_write_per_mtok
    ) / 1_000_000
    return round(dollars * 1_000_000)
