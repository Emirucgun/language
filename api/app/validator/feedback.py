"""Yazma geri bildirimi doğrulayıcısı (Technical MVP, 6: "Geri bildirim" satırı).

Geçemeyen geri bildirim öğrenciye gösterilmez; öğrenci "şimdilik atladık" görür ve
metin sonra yeniden işlenir. Hedef H4: yanlış öğretme ve cevabı ele verme sıfıra yakın.
"""

import re
from difflib import SequenceMatcher

from app.feedback.llm_schema import FoundError, WritingFeedback
from app.validator.core import Lexicon, ValidationResult, words

MAX_SHOWN = 2
MAX_HINT_CHARS = 120
# Düzeltme öğrencinin cümlesinden bu orandan fazla uzaklaşırsa "yeniden yazma" sayılır.
MIN_CORRECTION_SIMILARITY = 0.5
OTHER = "OTHER"


def _normalize(text: str) -> str:
    return " ".join(words(text))


def _check_consistency(fb: WritingFeedback, result: ValidationResult) -> None:
    if fb.is_correct:
        if fb.errors or fb.hint_tr or fb.correction:
            result.add("inconsistent", "doğru cümlede hata, ipucu ya da düzeltme olmamalı")
        return
    if not fb.errors:
        result.add("inconsistent", "yanlış denen cümlede hata listesi boş")
    if not fb.hint_tr:
        result.add("missing_hint", "hata var ama ipucu yok")
    if not fb.correction:
        result.add("missing_correction", "hata var ama düzeltme yok")


def _check_errors(
    fb: WritingFeedback, learner_text: str, catalog_codes: set[str], result: ValidationResult
) -> None:
    for error in fb.errors:
        if error.code != OTHER and error.code not in catalog_codes:
            result.add("unknown_code", error.code)
        if not 0 <= error.start <= error.end <= len(learner_text):
            result.add("bad_span", f"{error.code} {error.start}-{error.end}")


def _fix_words(learner_text: str, correction: str) -> set[str]:
    """Düzeltmede olup öğrencinin metninde olmayan kelimeler: cevabın kendisi."""
    return set(words(correction)) - set(words(learner_text))


def _check_hint(fb: WritingFeedback, learner_text: str, result: ValidationResult) -> None:
    if not fb.hint_tr:
        return
    if len(fb.hint_tr) > MAX_HINT_CHARS:
        result.add("hint_too_long", f"{len(fb.hint_tr)} karakter")
    if not fb.correction:
        return
    hint = fb.hint_tr.lower()
    if _normalize(fb.correction) and _normalize(fb.correction) in _normalize(fb.hint_tr):
        result.add("answer_leak", "ipucu düzeltilmiş cümleyi içeriyor")
        return
    for word in sorted(_fix_words(learner_text, fb.correction)):
        if re.search(rf"(?<![a-zçğıöşü]){re.escape(word)}(?![a-zçğıöşü])", hint):
            result.add("answer_leak", f"ipucu düzeltme kelimesini veriyor: {word!r}")


def _check_correction(
    fb: WritingFeedback, learner_text: str, lexicon: Lexicon, result: ValidationResult
) -> None:
    if fb.is_correct or not fb.correction:
        return
    learner_words, corrected_words = words(learner_text), words(fb.correction)
    if learner_words == corrected_words:
        result.add("no_change", "düzeltme öğrencinin cümlesiyle aynı")
    similarity = SequenceMatcher(None, learner_words, corrected_words).ratio()
    if similarity < MIN_CORRECTION_SIMILARITY:
        result.add("over_rewrite", f"benzerlik {similarity:.2f}")
    # Öğrencinin kendi kelimeleri serbest; seviye kontrolü yalnızca eklenen kelimelere.
    unknown = lexicon.out_of_level(fb.correction, also_allowed=learner_words)
    if unknown:
        result.add("out_of_level", ", ".join(unknown))


def validate_feedback(
    fb: WritingFeedback, *, learner_text: str, catalog_codes: set[str], lexicon: Lexicon
) -> ValidationResult:
    result = ValidationResult()
    _check_consistency(fb, result)
    _check_errors(fb, learner_text, catalog_codes, result)
    _check_hint(fb, learner_text, result)
    _check_correction(fb, learner_text, lexicon, result)
    return result


def shown_errors(fb: WritingFeedback) -> list[FoundError]:
    """Öğrenciye gösterilecek hatalar: en önemli ilk ikisi. Kalanlar yalnızca kaydedilir."""
    return fb.errors[:MAX_SHOWN]
