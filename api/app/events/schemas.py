"""Olay payload şemaları. `events` tablosuna yazılmadan önce her payload buradan doğrulanır.

Bir payload'un şekli değişirse `schema_version` artırılır ve eski sürümün modeli
silinmez: eski olaylar yeniden oynatılırken hâlâ okunabilmelidir.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Empty(Payload):
    pass


class ConsentGiven(Payload):
    consent_version: str
    is_adult_confirmed: Literal[True]


class GoalSet(Payload):
    goal: Literal["travel", "work", "school", "daily_conversation"]
    daily_minutes: int = Field(ge=5, le=120)
    weak_skills: list[Literal["reading", "writing", "listening", "vocabulary"]]
    interests: list[str] = Field(max_length=10)


class FixedTestAnswer(Payload):
    """Yerleştirme, ön/son test ve 14 gün hatırlama testi cevapları (H1, H3)."""

    test_id: int
    question_id: str
    answer: str
    correct: bool
    duration_ms: int | None = None


class FixedTestCompleted(Payload):
    test_id: int
    score: float
    cefr_estimate: str | None = None
    # Sonradan eklenen isteğe bağlı alanlar: eski olaylar da geçerli kalır (sürüm 1).
    sublevel: int | None = None
    level_scores: dict[str, float] | None = None


class AnswerSubmitted(Payload):
    """Etkinlik sorusu cevabı. FSRS derecesi olayın `rating` sütunundadır."""

    question_id: str
    answer: str
    correct: bool
    duration_ms: int | None = None


class WritingSubmitted(Payload):
    """Öğrencinin yazdığı metnin tek kopyası (silme talebinde redakte edilir)."""

    text: str = Field(max_length=1000)
    attempt: int = Field(ge=1)


class FeedbackReaction(Payload):
    """H5: geri bildirim sonrası "anladım / anlamadım"."""

    feedback_id: int
    understood: bool


class FeedbackShown(Payload):
    """Öğrenci geri bildirimi gördü. Gecikmeli geri bildirimde hangisi görüldü bilinsin diye
    `feedback_id` taşınır (sonradan eklenen isteğe bağlı alan; eski olaylar geçerli)."""

    feedback_id: int | None = None


class WritingAssessed(Payload):
    """Doğrulanmış geri bildirimin sonucu; hedef öğenin FSRS derecesi bu olayın `rating`'inde."""

    feedback_id: int
    is_correct: bool


class ActivityFlagged(Payload):
    reason: str | None = Field(default=None, max_length=500)


class ExtraActivityChosen(Payload):
    """H7: önerilen tür ile kullanıcının seçtiği tür ayrı kaydedilir."""

    recommended_kind: str | None
    chosen_kind: str


class DialogueReplied(Payload):
    """Partnerin bir öğrenci cümlesine cevabı. Konuşma geçmişi yalnızca olaylardan kurulur:
    öğrencinin cümlesi `writing_submitted`'ta, partnerinki burada (yalnızca eklenir)."""

    turn: int = Field(ge=1)
    writing_event_id: int
    feedback_id: int | None  # doğrulayıcıdan geçen geri bildirim yoksa None
    partner_en: str = Field(max_length=300)
    partner_tr: str = Field(max_length=300)
    source: Literal["llm", "fallback"]
    done: bool


class SessionCompleted(Payload):
    session_id: int


class NpsSubmitted(Payload):
    score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=1000)


# (tip, schema_version) -> payload modeli
PAYLOADS: dict[tuple[str, int], type[Payload]] = {
    ("consent_given", 1): ConsentGiven,
    ("goal_set", 1): GoalSet,
    ("fixed_test_answer", 1): FixedTestAnswer,
    ("fixed_test_completed", 1): FixedTestCompleted,
    ("curriculum_created", 1): Empty,
    ("curriculum_replanned", 1): Empty,
    ("activity_shown", 1): Empty,
    ("answer_submitted", 1): AnswerSubmitted,
    ("writing_submitted", 1): WritingSubmitted,
    ("rewrite_submitted", 1): WritingSubmitted,
    ("writing_assessed", 1): WritingAssessed,
    ("feedback_shown", 1): FeedbackShown,
    ("feedback_reaction", 1): FeedbackReaction,
    ("activity_flagged", 1): ActivityFlagged,
    ("extra_activity_chosen", 1): ExtraActivityChosen,
    ("dialogue_replied", 1): DialogueReplied,
    ("session_completed", 1): SessionCompleted,
    ("report_viewed", 1): Empty,
    ("nps_submitted", 1): NpsSubmitted,
}

CURRENT_VERSION: dict[str, int] = {}
for event_type, version in PAYLOADS:
    CURRENT_VERSION[event_type] = max(version, CURRENT_VERSION.get(event_type, 0))


def validate_payload(
    event_type: str, data: dict[str, object], version: int | None = None
) -> Payload:
    """Payload'u doğrular; bilinmeyen tip ya da sürüm `KeyError` verir."""
    schema_version = version if version is not None else CURRENT_VERSION[event_type]
    return PAYLOADS[(event_type, schema_version)].model_validate(data)
