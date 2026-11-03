from datetime import UTC, datetime, timedelta

from app.scheduler.engine import AnswerRating, apply_review, rating_for_answer, retrievability
from app.scheduler.service import fold_events

T0 = datetime(2026, 11, 9, 8, tzinfo=UTC)


def test_rating_rules() -> None:
    assert rating_for_answer(correct=False) is AnswerRating.AGAIN
    assert rating_for_answer(correct=True, hinted=True) is AnswerRating.HARD
    assert rating_for_answer(correct=True) is AnswerRating.GOOD


def test_same_reviews_give_same_state() -> None:
    # Bulanıklaştırma kapalı: yeniden oynatma için şart.
    def run() -> object:
        s = apply_review(None, AnswerRating.GOOD, T0)
        s = apply_review(s, AnswerRating.GOOD, T0 + timedelta(days=1))
        return apply_review(s, AnswerRating.AGAIN, T0 + timedelta(days=5))

    assert run() == run()


def test_good_answers_push_due_date_forward() -> None:
    first = apply_review(None, AnswerRating.GOOD, T0)
    second = apply_review(first, AnswerRating.GOOD, T0 + timedelta(days=1))
    third = apply_review(second, AnswerRating.GOOD, second.due)
    assert first.due < second.due < third.due
    assert third.reps == 3 and third.lapses == 0


def test_forgetting_a_review_item_counts_as_lapse() -> None:
    s = apply_review(None, AnswerRating.GOOD, T0)
    s = apply_review(s, AnswerRating.GOOD, T0 + timedelta(days=1))
    lapsed = apply_review(s, AnswerRating.AGAIN, s.due)
    assert lapsed.lapses == 1
    assert lapsed.due < s.due + timedelta(days=1)


def test_retrievability_decreases_over_time() -> None:
    s = apply_review(apply_review(None, AnswerRating.GOOD, T0), AnswerRating.GOOD, T0)
    assert retrievability(s, T0 + timedelta(days=1)) > retrievability(s, T0 + timedelta(days=30))


def test_incremental_fold_equals_full_replay() -> None:
    events = [
        (1, 10, 3, T0),
        (2, 11, 1, T0),
        (3, 10, 3, T0 + timedelta(days=1)),
        (4, 11, 3, T0 + timedelta(days=1)),
        (5, 10, 1, T0 + timedelta(days=8)),
    ]
    full = fold_events(events)
    partial = fold_events(events[:2])
    # Daha önce işlenmiş olaylar tekrar gelse de iki kez uygulanmaz.
    assert fold_events(events, partial) == full
