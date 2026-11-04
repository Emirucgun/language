"""Yazılı diyalog (rol yapma, 4–6 tur; blueprint, Bölüm 2 ve 6)."""

from pydantic import BaseModel, Field

from app.feedback.llm_schema import WritingFeedback
from app.feedback.service import FeedbackView

MIN_TURNS = 4
MAX_TURNS = 6


class PartnerLine(BaseModel):
    en: str = Field(description="Partner's next line in simple English, max 15 words.")
    tr: str = Field(description="Natural Turkish translation of the line.")


class DialogueTurn(BaseModel):
    """LLM çıktısı: öğrencinin son cümlesine geri bildirim + partnerin sıradaki cümlesi."""

    feedback: WritingFeedback
    partner: PartnerLine
    done: bool = Field(description="True when the conversation has reached a natural end.")


class TurnView(BaseModel):
    learner: str
    feedback: FeedbackView | None  # doğrulayıcıdan geçemezse gösterilmez
    partner: PartnerLine


class DialogueView(BaseModel):
    activity_id: int
    scenario_tr: str
    learner_role_tr: str
    partner_role_tr: str
    target_items: list[str]
    opening: PartnerLine
    turns: list[TurnView]
    min_turns: int = MIN_TURNS
    max_turns: int = MAX_TURNS
    done: bool


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)
