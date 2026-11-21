"""Denetimli ses üretimi: sohbet modeli cümleyi okumayabilir, bu yüzden her ses dinlenir.

Ölçüm (`docs/experiments/2026-11-04-tts-realtime.md`): 120 üretimin 3'ünde model kendi
cümlesini kurdu ya da başına cümle ekledi. Dinleyen model ise doğru sesi de farklı yazabilir
(seven thirty -> 7:30, We're -> We are, Elif -> Alif), bu yüzden tam eşleşme aranmaz:
- modelin dökümü metinle aynı olmalı,
- dinlenen metin belirgin biçimde uzun olmamalı (eklenen cümleyi yakalar),
- kelimeler yeterince örtüşmeli (bambaşka cümleyi yakalar).
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.tts.client import Transcriber, TTSClient, TTSFailed, TTSRequest, TTSResult, audio_matches
from app.validator.core import words

MAX_EXTRA_WORDS = 1  # We're -> We are
MIN_SIMILARITY = 0.6
MAX_ATTEMPTS = 3
CONTRACTIONS = {"re": "are", "s": "is", "m": "am", "ve": "have", "ll": "will", "d": "would"}


@dataclass(frozen=True, slots=True)
class CheckedSpeech:
    result: TTSResult
    heard: str
    attempts: int
    total_cost_microusd: int
    rejected: tuple[str, ...]  # reddedilen üretimlerde dinlenen metin


def _expanded(text: str) -> list[str]:
    """Dinleyen model kısaltmayı açabilir; kısa cümlede bu tek fark eşiği düşürür."""
    tokens: list[str] = []
    for token in words(text):
        head, _, tail = token.partition("'")
        if tail == "t" and head.endswith("n"):
            tokens += [head[:-1], "not"]
        elif tail in CONTRACTIONS:
            tokens += [head, CONTRACTIONS[tail]]
        else:
            tokens.append(token)
    return tokens


def speech_ok(text: str, transcript: str | None, heard: str) -> bool:
    expected, got = _expanded(text), _expanded(heard)
    if not audio_matches(text, transcript) or len(got) > len(expected) + MAX_EXTRA_WORDS:
        return False
    return SequenceMatcher(None, expected, got).ratio() >= MIN_SIMILARITY


def synthesize_checked(
    speech: TTSClient, listener: Transcriber, request: TTSRequest
) -> CheckedSpeech:
    """Denetimden geçen sesi döndürür; geçemezse `TTSFailed`. Reddedilen üretim de ücretlidir."""
    cost = 0
    rejected: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = speech.synthesize(request)
        cost += result.cost_microusd or 0
        heard = listener.transcribe(result.audio_wav)
        if speech_ok(request.text, result.transcript, heard):
            return CheckedSpeech(result, heard, attempt, cost, tuple(rejected))
        rejected.append(heard)
    raise TTSFailed(f"{MAX_ATTEMPTS} denemede okunamadı: {request.text!r}")
