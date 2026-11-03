"""Yazma geri bildiriminin LLM çıktı şeması.

Bilerek dar: LLM Türkçe açıklama yazmaz (katalogdan gelir) ve öğrencinin metnini
geri yankılamaz; yalnızca hata kodu, metindeki konumu, kısa bir ipucu ve doğru cümle.
"""

from pydantic import BaseModel, Field


class FoundError(BaseModel):
    code: str = Field(description="Error code from the catalog, or OTHER.")
    start: int = Field(description="Start character offset in the student's text.")
    end: int = Field(description="End character offset (exclusive).")


class WritingFeedback(BaseModel):
    is_correct: bool
    errors: list[FoundError] = Field(description="Most important first.")
    hint_tr: str | None = Field(
        description="One short Turkish hint that does not reveal the corrected sentence."
    )
    correction: str | None = Field(description="Corrected sentence, shown only after rewrite.")
