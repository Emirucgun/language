"""Etkinlik başına doğrulama (docs/architecture/validator.md)."""

from dataclasses import dataclass

from app.sessions.schemas import BLANK, Choice, NewItem, Reading, Recall, Writing
from app.validator.activity import (
    READING_WORDS,
    check_level,
    check_no_answer_leak,
    check_single_answer,
    check_target_used,
    check_word_count,
)
from app.validator.core import Lexicon, ValidationResult

# Prompt'ta izin verilen isimler ve şehirler (prompts/session/v2.md ile aynı).
NAMES = ("Ali", "Ayşe", "Mehmet", "Zeynep", "Elif", "Tom", "Anna")
PLACES = ("Istanbul", "Ankara", "Izmir", "London", "Paris")


@dataclass(frozen=True, slots=True)
class ItemCard:
    """LLM'e ve doğrulayıcıya giden öğe bilgisi."""

    id: int
    text_en: str
    text_tr: str
    forms: tuple[str, ...]

    @property
    def all_forms(self) -> tuple[str, ...]:
        return (self.text_en, *self.forms)


def _allowed(cards: list[ItemCard]) -> list[str]:
    return [*NAMES, *PLACES, *(f for c in cards for f in c.all_forms)]


def _check_choice(
    choice: Choice,
    card: ItemCard,
    lexicon: Lexicon,
    result: ValidationResult,
    *,
    gap: bool,
) -> None:
    check_single_answer(choice.options, choice.answer, result)
    if len(choice.options) != 3:
        result.add("option_count", str(len(choice.options)))
    if gap:
        if choice.prompt.count(BLANK) != 1:
            result.add("gap_count", choice.prompt)
        check_no_answer_leak(choice.prompt.replace(BLANK, " "), [choice.answer], result)
        check_target_used(choice.prompt.replace(BLANK, choice.answer), card.all_forms, result)
    allowed = _allowed([card])
    check_level(choice.prompt.replace(BLANK, " "), lexicon, result, allowed)
    for option in choice.options:
        check_level(option, lexicon, result, allowed)


def validate_recall(a: Recall, card: ItemCard, lexicon: Lexicon) -> ValidationResult:
    result = ValidationResult()
    _check_choice(a.question, card, lexicon, result, gap=True)
    check_no_answer_leak(a.hint_tr, [a.question.answer], result)
    return result


def validate_new_item(a: NewItem, card: ItemCard, lexicon: Lexicon) -> ValidationResult:
    result = ValidationResult()
    if len(a.examples) != 2:
        result.add("example_count", str(len(a.examples)))
    if len(a.meaning_tr) > 160:
        result.add("meaning_too_long", f"{len(a.meaning_tr)} karakter")
    for example in a.examples:
        check_target_used(example.en, card.all_forms, result)
        check_level(example.en, lexicon, result, _allowed([card]))
    _check_choice(a.check, card, lexicon, result, gap=True)
    return result


def validate_reading(a: Reading, cards: list[ItemCard], lexicon: Lexicon) -> ValidationResult:
    result = ValidationResult()
    check_word_count(a.text_en, READING_WORDS, result)
    check_level(a.text_en, lexicon, result, _allowed(cards))
    used = [c for c in cards if c.id in a.item_ids]
    if not used:
        result.add("target_missing", "okuma metni hedef öğe kullanmıyor")
    for card in used:
        check_target_used(a.text_en, card.all_forms, result)
    if len(a.questions) != 2:
        result.add("question_count", str(len(a.questions)))
    for question in a.questions:
        check_single_answer(question.options, question.answer, result)
        check_level(question.prompt, lexicon, result, _allowed(cards))
    return result


def validate_writing(a: Writing, card: ItemCard) -> ValidationResult:
    result = ValidationResult()
    check_target_used(a.task_en, card.all_forms, result)
    if not a.task_tr.strip():
        result.add("missing_task_tr", "Türkçe yönerge boş")
    return result
