"""Müfredat: ajanın (LLM) önerisi ve kural katmanının onayladığı hali.

Ajan yalnızca havuzdaki öğelerden, seviye sınırları içinde plan kurabilir; kural katmanı
her öneriyi doğrular (Technical MVP, 3: "Müfredat ajanı öneri yapar, kural katmanı onaylar").
Süre ve seviye vaat değil tahmindir: ekranda aralık olarak gösterilir.
"""

from pydantic import BaseModel, Field

SKILLS = ("vocabulary", "reading", "listening", "writing")


class SkillWeights(BaseModel):
    vocabulary: float = Field(ge=0, le=1)
    reading: float = Field(ge=0, le=1)
    listening: float = Field(ge=0, le=1)
    writing: float = Field(ge=0, le=1)


class WeekDraft(BaseModel):
    week: int
    focus_tr: str = Field(description="Short Turkish title for the week's theme (max 60 chars).")
    item_ids: list[int] = Field(description="Item ids introduced this week, in teaching order.")
    can_do_tr: list[str] = Field(
        description="1-3 Turkish 'can-do' statements the learner should manage by week end."
    )
    skill_weights: SkillWeights


class CurriculumDraft(BaseModel):
    summary_tr: str = Field(description="Two short Turkish sentences describing the plan.")
    weeks: list[WeekDraft]


class WeekView(BaseModel):
    week: int
    focus_tr: str
    can_do_tr: list[str]
    item_count: int
    items_en: list[str]
    current: bool
    skill_weights: SkillWeights


class CurriculumView(BaseModel):
    version: int
    summary_tr: str
    weeks: list[WeekView]
    current_week: int
    # Tahmin aralığı: vaat değil (blueprint, SK6).
    estimate_tr: str
