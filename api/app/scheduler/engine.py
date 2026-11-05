"""FSRS sarmalayıcısı: saf fonksiyonlar, veritabanı ve LLM'den bağımsız.

Bulanıklaştırma (fuzzing) kapalı: aynı olay dizisi her zaman aynı durumu üretmeli,
yoksa olay kaydından yeniden oynatma artımlı güncellemeyle eşleşmez.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum

from fsrs import Card, Rating, Scheduler, State

SCHEDULER = Scheduler(desired_retention=0.9, enable_fuzzing=False)


class AnswerRating(IntEnum):
    """Olayların `rating` sütunundaki değerler (FSRS ile aynı sayılar)."""

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


def rating_for_choice(
    *, correct: bool, hinted: bool = False, reviewing: bool = False
) -> AnswerRating:
    """Şıklı cevaptan FSRS derecesi. Kural katmanı karar verir; LLM bu değeri üretmez.

    Şıkta tahmin şansı var, bu yüzden tekrar aşamasında doğru yalnızca Hard sayılır. Öğrenme
    aşamasında Good kalır: FSRS'te Hard öğrenmeden çıkarmaz, her zaman doğru bilen öğrenci
    8 haftada 68 kez tekrar ederdi (docs/experiments/2026-11-05-derece-eslemesi.md).

    "Easy" bilerek kullanılmıyor: A1–A2'de tek doğru cevap ezberi aşırı güveni beslemesin.
    """
    if not correct:
        return AnswerRating.AGAIN
    return AnswerRating.HARD if hinted or reviewing else AnswerRating.GOOD


def rating_for_writing(*, correct: bool) -> AnswerRating:
    """İpucusuz yazılı üretim en güçlü kanıttır; tahmin edilemez."""
    return AnswerRating.GOOD if correct else AnswerRating.AGAIN


def is_reviewing(state: int | None) -> bool:
    """Öğe öğrenme aşamasını bitirmiş mi?"""
    return state == State.Review


@dataclass(frozen=True, slots=True)
class CardState:
    """`learning.item_states` satırının bellekteki karşılığı (filigran hariç)."""

    state: int
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime | None
    reps: int
    lapses: int


def _utc(value: datetime) -> datetime:
    # FSRS yalnızca UTC kabul eder; veritabanı oturum saat dilimiyle döndürebilir.
    return value.astimezone(UTC)


def _to_card(state: CardState) -> Card:
    return Card(
        state=State(state.state),
        step=state.step,
        stability=state.stability,
        difficulty=state.difficulty,
        due=_utc(state.due),
        last_review=_utc(state.last_review) if state.last_review else None,
    )


def apply_review(previous: CardState | None, rating: int, reviewed_at: datetime) -> CardState:
    """Bir derecelendirmeyi uygular. `previous` yoksa öğe ilk kez görülüyordur."""
    reviewed_at = _utc(reviewed_at)
    card = Card(due=reviewed_at) if previous is None else _to_card(previous)
    reviewed, _ = SCHEDULER.review_card(card, Rating(rating), reviewed_at)

    reps = previous.reps if previous else 0
    lapses = previous.lapses if previous else 0
    lapsed = previous is not None and previous.state == State.Review and rating == Rating.Again
    assert reviewed.due is not None  # review_card her zaman bir vade atar
    return CardState(
        state=int(reviewed.state),
        step=reviewed.step,
        stability=reviewed.stability,
        difficulty=reviewed.difficulty,
        due=reviewed.due,
        last_review=reviewed.last_review,
        reps=reps + 1,
        lapses=lapses + (1 if lapsed else 0),
    )


def retrievability(state: CardState, at: datetime) -> float:
    """Öğenin `at` anında hatırlanma olasılığı (0–1)."""
    return float(SCHEDULER.get_card_retrievability(_to_card(state), _utc(at)))
