import os
import uuid

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.feedback.llm_schema import FoundError, WritingFeedback
from app.validator.activity import (
    READING_WORDS,
    check_audio_matches,
    check_level,
    check_no_answer_leak,
    check_single_answer,
    check_target_used,
    check_word_count,
)
from app.validator.core import Lexicon, ValidationResult, load_lexicon
from app.validator.feedback import shown_errors, validate_feedback
from tests.conftest import _libpq_url

A1_WORDS = (
    "i you he she it we they my your his her a an the is am are be work works as "
    "teacher teachers city very big small in on at go goes went to school home "
    "like likes coffee tea every day and"
)
LEXICON = Lexicon(frozenset(A1_WORDS.split()))
CODES = {"ARTICLE", "BE_VERB", "PREPOSITION"}


def _fb(**kwargs: object) -> WritingFeedback:
    base: dict[str, object] = {
        "is_correct": False,
        "errors": [{"code": "ARTICLE", "start": 10, "end": 10}],
        "hint_tr": "Meslekten önce küçük bir kelime eksik.",
        "correction": "I work as a teacher.",
    }
    return WritingFeedback.model_validate(base | kwargs)


def _check(fb: WritingFeedback, text: str = "I work as teacher.") -> set[str]:
    result = validate_feedback(fb, learner_text=text, catalog_codes=CODES, lexicon=LEXICON)
    return {i.code for i in result.issues}


# --- Geri bildirim -----------------------------------------------------------


def test_prompt_examples_pass() -> None:
    assert _check(_fb()) == set()
    correct = _fb(is_correct=True, errors=[], hint_tr=None, correction=None)
    assert _check(correct, "my city is very big") == set()
    two_errors = _fb(
        errors=[
            {"code": "BE_VERB", "start": 4, "end": 4},
            {"code": "ARTICLE", "start": 4, "end": 4},
        ],
        hint_tr="Özne ile meslek arasında bir fiil eksik.",
        correction="She is a teacher.",
    )
    assert _check(two_errors, "She teacher.") == set()


@pytest.mark.parametrize(
    "hint",
    ["Mesleğin önüne 'a' koy.", "Doğrusu: I work as a teacher."],
)
def test_hint_that_gives_the_answer_is_rejected(hint: str) -> None:
    assert "answer_leak" in _check(_fb(hint_tr=hint))


def test_hint_may_quote_the_learners_own_words() -> None:
    assert _check(_fb(hint_tr="'teacher' kelimesinden önce bir şey eksik.")) == set()


def test_correct_sentence_must_not_carry_errors() -> None:
    fb = _fb(is_correct=True)
    assert "inconsistent" in _check(fb)


def test_error_needs_hint_and_correction() -> None:
    issues = _check(_fb(hint_tr=None, correction=None))
    assert {"missing_hint", "missing_correction"} <= issues


def test_unknown_code_and_bad_span() -> None:
    issues = _check(_fb(errors=[{"code": "MADE_UP", "start": 5, "end": 99}]))
    assert {"unknown_code", "bad_span"} <= issues
    assert _check(_fb(errors=[{"code": "OTHER", "start": 0, "end": 1}])) == set()


def test_full_rewrite_is_rejected() -> None:
    issues = _check(_fb(correction="Teaching is my profession these days."))
    assert "over_rewrite" in issues
    assert "out_of_level" in issues


def test_unchanged_correction_is_rejected() -> None:
    assert "no_change" in _check(_fb(correction="I work as teacher"))


def test_long_hint_is_rejected() -> None:
    assert "hint_too_long" in _check(_fb(hint_tr="Bir kelime eksik. " * 10))


def test_only_two_errors_are_shown() -> None:
    errors = [FoundError(code="ARTICLE", start=0, end=0) for _ in range(4)]
    assert len(shown_errors(_fb(errors=[e.model_dump() for e in errors]))) == 2


# --- Etkinlikler -------------------------------------------------------------


def test_level_allows_targets_and_names() -> None:
    result = ValidationResult()
    check_level("My city is Istanbul and I like coffee.", LEXICON, result)
    assert result.ok
    # Cümle başındaki isim sıradan kelimeden ayırt edilemez; üretici isimleri açıkça verir.
    check_level("Ali likes coffee.", LEXICON, result, target_forms=["Ali"])
    assert result.ok
    check_level("She commutes to work.", LEXICON, result, target_forms=["commute", "commutes"])
    assert result.ok
    check_level("She is extraordinarily busy.", LEXICON, result)
    assert [i.code for i in result.issues] == ["out_of_level"]


@pytest.mark.parametrize(
    "inflected", ["teachers", "works", "goes", "working", "liked", "bigger", "cities"]
)
def test_regular_inflections_are_in_level(inflected: str) -> None:
    lexicon = Lexicon(frozenset({"teacher", "work", "go", "like", "big", "city"}))
    assert lexicon.out_of_level(inflected) == []


def test_unknown_stems_are_still_out_of_level() -> None:
    assert Lexicon(frozenset({"work"})).out_of_level("chefs cooking") == ["chefs", "cooking"]


def test_target_item_must_appear_including_chunks() -> None:
    result = ValidationResult()
    check_target_used("I go to school every day.", ["every day"], result)
    check_target_used("He goes home.", ["go", "goes", "went"], result)
    assert result.ok
    check_target_used("I like tea.", ["coffee"], result)
    assert not result.ok


def test_answer_must_not_leak_into_question() -> None:
    result = ValidationResult()
    check_no_answer_leak("I ___ as a teacher. (çalışmak)", ["work"], result)
    assert result.ok
    check_no_answer_leak("I ___ as a teacher. Hint: work", ["work"], result)
    assert [i.code for i in result.issues] == ["answer_leak"]


def test_multiple_choice_needs_one_correct_unique_option() -> None:
    result = ValidationResult()
    check_single_answer(["in", "on", "at"], "at", result)
    assert result.ok
    check_single_answer(["in", "In", "at"], "at", result)
    check_single_answer(["in", "on"], "at", result)
    assert [i.code for i in result.issues] == ["duplicate_options", "answer_not_unique"]


def test_audio_and_length_checks() -> None:
    result = ValidationResult()
    check_audio_matches("I like tea.", "I like tea", result)
    assert result.ok
    check_audio_matches("I like tea.", "I like coffee.", result)
    check_word_count("too short", READING_WORDS, result)
    assert [i.code for i in result.issues] == ["audio_mismatch", "length"]


def test_result_is_storable() -> None:
    result = ValidationResult()
    result.add("answer_leak", "work")
    assert result.to_dict() == {
        "version": "v1",
        "ok": False,
        "issues": [{"code": "answer_leak", "detail": "work"}],
    }


# --- Sözlük veritabanından ----------------------------------------------------


def test_lexicon_loads_allowlist_and_item_forms(migrated_db: Config) -> None:
    lemma = "zz" + "".join(chr(97 + int(c, 16)) for c in uuid.uuid4().hex[:8])
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.vocab_allowlist (lemma, cefr, forms, source) "
            "VALUES (%s, 'A1', ARRAY[%s], 'test'), (%s, 'B2', '{}', 'test')",
            (lemma, lemma + "s", lemma + "b2"),
        )
        conn.execute(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, forms) "
            "VALUES ('test', 'chunk', %s, 'x', 'A2', ARRAY[%s])",
            (f"look {lemma}x", lemma + "ed"),
        )
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as session:
        lexicon = load_lexicon(session)
    engine.dispose()
    assert {lemma, lemma + "s", lemma + "x", lemma + "ed"} <= lexicon.forms
    assert lemma + "b2" not in lexicon.forms


def test_multiword_allowlist_entries_contribute_their_words(migrated_db: Config) -> None:
    phrase = "zz" + "".join(chr(97 + int(c, 16)) for c in uuid.uuid4().hex[:6])
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.vocab_allowlist (lemma, cefr, source) VALUES (%s, 'A1', 'test')",
            (f"a {phrase}",),
        )
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as session:
        assert phrase in load_lexicon(session).forms
    engine.dispose()
