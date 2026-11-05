from datetime import UTC, datetime, timedelta

from app.scheduler.engine import (
    AnswerRating,
    apply_review,
    is_reviewing,
    rating_for_choice,
    rating_for_writing,
    retrievability,
)
from app.scheduler.service import fold_events

T0 = datetime(2026, 11, 9, 8, tzinfo=UTC)


def test_correct_choice_counts_less_once_the_item_is_in_review() -> None:
    """Şıkta tahmin şansı var; ama öğrenme aşamasında Hard öğeyi kilitlerdi."""
    assert rating_for_choice(correct=True, reviewing=False) is AnswerRating.GOOD
    assert rating_for_choice(correct=True, reviewing=True) is AnswerRating.HARD
    assert rating_for_choice(correct=False, reviewing=True) is AnswerRating.AGAIN


def test_written_production_is_the_strongest_evidence() -> None:
    assert rating_for_writing(correct=True) is AnswerRating.GOOD
    assert rating_for_writing(correct=False) is AnswerRating.AGAIN


def test_choice_only_learner_is_not_stuck_in_daily_reviews() -> None:
    """Hep Hard deseydik öğe 8 haftada 68 kez tekrar edilirdi; kural bunu önler."""
    state, now, reviews = None, T0, 0
    while now < T0 + timedelta(days=56):
        reviewing = state is not None and is_reviewing(state.state)
        state = apply_review(state, rating_for_choice(correct=True, reviewing=reviewing), now)
        reviews += 1
        now = max(state.due, now + timedelta(hours=20))
    assert reviews <= 8
    assert state is not None and is_reviewing(state.state)


def test_rating_rules() -> None:
    assert rating_for_choice(correct=False) is AnswerRating.AGAIN
    assert rating_for_choice(correct=True, hinted=True) is AnswerRating.HARD
    assert rating_for_choice(correct=True) is AnswerRating.GOOD


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
