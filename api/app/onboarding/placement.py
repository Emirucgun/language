"""Yerleştirme testi: sabit, sürümlü sorular ve deterministik puanlama (blueprint, Bölüm 3).

Test canlı üretilmez: kullanıcılar arasında karşılaştırılabilir olmalı (H3: ön/son test).
Sorular `content.fixed_tests` tablosundadır; içerik Işıl onayıyla sürümlenir.

Puanlama (bilerek basit ve açıklanabilir):
  - A1 sorularının %50'sinden azı doğruysa → "pre-A1" (A1 başlangıcından başlar)
  - değilse A2 sorularının %50'sinden azı doğruysa → A1 (A1 ≥ %80 ise A1.2, yoksa A1.1)
  - değilse → A2 (A2 ≥ %80 ise A2.2, yoksa A2.1)
"Bilmiyorum" cevabı yanlış sayılır; tahmin etmeyi azaltır.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["vocabulary", "grammar", "reading", "listening"]
PASS = 0.5
STRONG = 0.8


class FixedQuestion(BaseModel):
    id: str
    section: Section
    level: Literal["A1", "A2"]
    prompt: str
    options: list[str] = Field(min_length=2, max_length=4)
    answer: str
    passage: str | None = None  # okuma soruları aynı metni paylaşır


class FixedQuestionView(BaseModel):
    """Öğrenciye giden hali: cevap yok."""

    id: str
    section: Section
    prompt: str
    options: list[str]
    passage: str | None = None


@dataclass(frozen=True, slots=True)
class Placement:
    cefr_estimate: Literal["pre-A1", "A1", "A2"]
    sublevel: int
    level_scores: dict[str, float]
    score: float

    @property
    def start_level(self) -> str:
        """Etkinlik üretiminde kullanılan seviye: pre-A1 de A1 başlangıcından başlar."""
        return "A2" if self.cefr_estimate == "A2" else "A1"

    @property
    def cefr_sub(self) -> str:
        return f"{self.start_level}.{self.sublevel}"


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def is_correct(question: FixedQuestion, answer: str) -> bool:
    return bool(answer) and normalize(answer) == normalize(question.answer)


def score(questions: list[FixedQuestion], answers: dict[str, str]) -> Placement:
    """Cevaplanmamış soru yanlış sayılır."""
    by_level: dict[str, list[bool]] = {"A1": [], "A2": []}
    for q in questions:
        by_level[q.level].append(is_correct(q, answers.get(q.id, "")))
    ratio = {lvl: (sum(r) / len(r) if r else 0.0) for lvl, r in by_level.items()}
    total = sum(sum(r) for r in by_level.values()) / max(1, len(questions))

    if ratio["A1"] < PASS:
        return Placement("pre-A1", 1, ratio, total)
    if ratio["A2"] < PASS:
        return Placement("A1", 2 if ratio["A1"] >= STRONG else 1, ratio, total)
    return Placement("A2", 2 if ratio["A2"] >= STRONG else 1, ratio, total)
