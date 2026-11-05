"""Oranların güven sınırı. Küçük örnekte "hiç hata çıkmadı" kanıt değildir.

Clopper-Pearson, tek yönlü %95: 100 yargıda sıfır hata bile üst sınırı yaklaşık %3 yapar.
Saf Python: yalnızca birkaç yüz yargı için çalışır, bağımlılık eklemeye değmez.
"""

from math import comb

CONFIDENCE = 0.95


def _at_most(k: int, n: int, p: float) -> float:
    """Binom dağılımında en fazla k başarı olasılığı."""
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def upper_bound(k: int, n: int, confidence: float = CONFIDENCE) -> float:
    """Gerçek oranın üst sınırı: k/n gözlendiyse oran bundan büyük olamaz (güvenle)."""
    if n <= 0:
        raise ValueError("örnek boş")
    if k >= n:
        return 1.0
    alpha = 1 - confidence
    low, high = k / n, 1.0
    for _ in range(60):
        middle = (low + high) / 2
        if _at_most(k, n, middle) > alpha:
            low = middle
        else:
            high = middle
    return high


def lower_bound(k: int, n: int, confidence: float = CONFIDENCE) -> float:
    """Başarı oranı için alt sınır: başarısızlıkların üst sınırının tümleyeni."""
    return 1 - upper_bound(n - k, n, confidence)
