"""Model fiyatları ve çağrı maliyeti (mikro-dolar). Kaynak: liste fiyatları, Kas 2026.

Anthropic önbelleği: 1 saatlik yazma girdinin 2 katı, 5 dakikalık 1.25 katı, okuma 0.1 katı.
Statik bloklar 1 saatlik önbelleğe yazılır; hesap bu yüzden tutucu olarak 2 katı kullanır.

OpenAI önbelleği: 30 dakikalık yazma 1.25 katı (12 saatlik 2.5 katı kullanılmıyor), okuma
tabloda; Sol ve Terra'da 0.05 katı.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Price:
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float
    cache_write_per_mtok: float


def _claude(input_price: float, output_price: float) -> Price:
    return Price(input_price, output_price, input_price * 0.1, input_price * 2)


PRICES: dict[str, Price] = {
    "claude-haiku-5-5": _claude(0.10, 0.50),
    "claude-sonnet-5-5": _claude(2.00, 10.00),
    "claude-opus-5-5": _claude(4.00, 20.00),
    "gpt-6-luna": Price(0.10, 0.50, 0.01, 0.125),
    "gpt-6.1-sol": Price(2.00, 10.00, 0.10, 2.50),
    "gpt-6.1-terra": Price(1.00, 5.00, 0.05, 1.25),
}


@dataclass(frozen=True, slots=True)
class Usage:
    """Sağlayıcıdan bağımsız: `input_tokens` önbellek dışı girdidir, adaptör buna çevirir."""

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
