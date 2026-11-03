"""Sürümlü prompt dosyaları: `prompts/<purpose>/<version>.md`.

Statik blok bayt bayt sabit kalmalı; yoksa önbellek her çağrıda kırılır. Bu yüzden
yer tutucular yalnızca deterministik (sıralı) içerikle doldurulur, zaman ya da kimlik
gibi değişken değerler buraya asla girmez. İçerik değişirse sürüm artırılır.
"""

import re
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"
_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


@cache
def _read(purpose: str, version: str) -> str:
    return (PROMPTS_DIR / purpose / f"{version}.md").read_text(encoding="utf-8")


def render_static(purpose: str, version: str, values: dict[str, str] | None = None) -> str:
    template = _read(purpose, version)
    values = values or {}
    missing = set(_PLACEHOLDER.findall(template)) - values.keys()
    if missing:
        raise KeyError(f"{purpose}/{version} için eksik yer tutucu: {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def estimate_tokens(text: str) -> int:
    """Kaba tahmin (~4 karakter/token). Kesin sayı `llm_calls`'taki gerçek kullanımdan gelir."""
    return max(1, len(text) // 4)
