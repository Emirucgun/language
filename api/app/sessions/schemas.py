"""Etkinlik şemaları: LLM çıktısı (cevaplar dahil) ve öğrenciye giden görünüm (cevapsız).

Çıktı şeması bilerek düz: birleşik (union) tipler yerine tür başına liste. Her etkinlik
ayrı doğrulanır; kalan tek etkinlik yeniden üretilir ya da şablona düşer.
"""

from typing import Literal

from pydantic import BaseModel, Field

BLANK = "___"


class Choice(BaseModel):
    """Tek doğru cevaplı çoktan seçmeli soru."""

    prompt: str = Field(description="Question text in English. Recall prompts contain ___ once.")
    options: list[str] = Field(description="Exactly 3 options, one of them correct.")
    answer: str = Field(description="The correct option, copied exactly.")


class Recall(BaseModel):
    item_id: int
    question: Choice
    hint_tr: str = Field(description="Turkish meaning of the full sentence; never the answer.")


class Example(BaseModel):
    en: str
    tr: str


class NewItem(BaseModel):
    item_id: int
    meaning_tr: str = Field(description="One short Turkish sentence explaining the item.")
    examples: list[Example] = Field(description="Exactly 2 examples using the item.")
    check: Choice


class Reading(BaseModel):
    item_ids: list[int]
    text_en: str = Field(description="50-80 words, A1-A2.")
    questions: list[Choice] = Field(description="Exactly 2 comprehension questions.")


class Writing(BaseModel):
    item_id: int
    task_en: str = Field(description="One-sentence writing task in English for the model.")
    task_tr: str = Field(description="The same task in simple Turkish for the learner.")


class SessionOutput(BaseModel):
    recall: list[Recall]
    new_items: list[NewItem]
    reading: list[Reading]
    writing: list[Writing]


Kind = Literal["recall", "new_item", "reading", "writing"]
ActivityModel = Recall | NewItem | Reading | Writing


# --- Öğrenciye giden görünüm: cevaplar yok ---------------------------------


class ChoiceView(BaseModel):
    id: str
    prompt: str
    options: list[str]


class ActivityView(BaseModel):
    id: int
    kind: Kind
    recommended: bool
    done: bool
    # Türüne göre dolu alanlar
    hint_tr: str | None = None
    meaning_tr: str | None = None
    item_en: str | None = None
    examples: list[Example] | None = None
    text_en: str | None = None
    task_tr: str | None = None
    questions: list[ChoiceView] = []


class SessionView(BaseModel):
    id: int
    local_date: str
    status: str
    activities: list[ActivityView]


class AnswerRequest(BaseModel):
    question_id: str = Field(max_length=8)
    answer: str = Field(max_length=200)
    hinted: bool = False
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class AnswerResult(BaseModel):
    correct: bool
    correct_answer: str
