"""Yazma geri bildiriminin LLM çıktı şeması.

Bilerek dar: LLM Türkçe açıklama yazmaz (katalogdan gelir) ve öğrencinin metnini
geri yankılamaz; yalnızca hata kodu, hatanın yeri, kısa bir ipucu ve doğru cümle.

Hatanın yeri karakter konumu olarak istenmez: model konumu sık kaydırıyor (4 Kas 2026,
"I work as engineer" denemesi). Model hatalı kelimeleri alıntılar, konumu sunucu bulur
(`app/validator/feedback.py: span_of`).
"""

from typing import Literal

from pydantic import BaseModel, Field


class FoundError(BaseModel):
    code: str = Field(description="Error code from the catalog, or OTHER.")
    quote: str = Field(
        description="Exact word(s) copied from the learner's text where the error is. "
        "For a missing word: the word right next to the gap."
    )
    gap: Literal["none", "before", "after"] = Field(
        description="none: the quoted words are wrong. before/after: a word is missing "
        "right before/after the quoted words."
    )


class WritingFeedback(BaseModel):
    is_correct: bool
    errors: list[FoundError] = Field(description="Most important first.")
    hint_tr: str | None = Field(
        description="One short Turkish hint that does not reveal the corrected sentence."
    )
    correction: str | None = Field(description="Corrected sentence, shown only after rewrite.")
