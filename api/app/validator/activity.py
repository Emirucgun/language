"""Canlı üretilen etkinliklerin kontrolleri (docs/architecture/validator.md).

Her etkinlik türü kendi şemasını bu yapı taşlarıyla doğrular. Geçemeyen etkinlik bir kez
yeniden üretilir, sonra yedek şablona düşer.
"""

from collections.abc import Sequence

from app.validator.core import Lexicon, ValidationResult, words

READING_WORDS = (50, 80)  # mikro okuma uzunluğu (blueprint, Bölüm 6)


def _phrase(text: str) -> str:
    return " " + " ".join(words(text)) + " "


def check_level(
    text: str, lexicon: Lexicon, result: ValidationResult, target_forms: Sequence[str] = ()
) -> None:
    """Seviye dışı kelime yok. `target_forms` her zaman serbesttir.

    Cümle ortasındaki büyük harfli isimler otomatik muaf; cümle başındaki bir isim
    sıradan kelimeden ayırt edilemediği için üretici, kullandığı isimleri de buraya verir.
    """
    allowed = [w for form in target_forms for w in words(form)]
    unknown = lexicon.out_of_level(text, also_allowed=allowed)
    if unknown:
        result.add("out_of_level", ", ".join(unknown))


def check_target_used(text: str, target_forms: Sequence[str], result: ValidationResult) -> None:
    """Hedef öğe (çok kelimeli kalıplar dahil) metinde bir biçimiyle geçmeli."""
    haystack = _phrase(text)
    if not any(_phrase(form) in haystack for form in target_forms if words(form)):
        result.add("target_missing", " / ".join(target_forms))


def check_no_answer_leak(
    prompt_text: str, accepted_answers: Sequence[str], result: ValidationResult
) -> None:
    """Soru metni (ipucu dahil) doğru cevabı içermemeli."""
    haystack = _phrase(prompt_text)
    for answer in accepted_answers:
        if words(answer) and _phrase(answer) in haystack:
            result.add("answer_leak", answer)


def check_single_answer(options: Sequence[str], answer: str, result: ValidationResult) -> None:
    """Çoktan seçmelide şıklar birbirinden farklı ve doğru cevap tam bir kez var."""
    normalized = [" ".join(words(o)) for o in options]
    if len(set(normalized)) != len(normalized):
        result.add("duplicate_options", " | ".join(options))
    matches = normalized.count(" ".join(words(answer)))
    if matches != 1:
        result.add("answer_not_unique", f"{answer!r} şıklarda {matches} kez")


def check_audio_matches(display_text: str, audio_text: str, result: ValidationResult) -> None:
    """TTS'e giden metin, ekranda doğrulanan metinle aynı olmalı."""
    if words(display_text) != words(audio_text):
        result.add("audio_mismatch", "seslendirme metni ekrandakinden farklı")


def check_word_count(
    text: str, bounds: tuple[int, int], result: ValidationResult, code: str = "length"
) -> None:
    count = len(words(text))
    low, high = bounds
    if not low <= count <= high:
        result.add(code, f"{count} kelime (beklenen {low}-{high})")
