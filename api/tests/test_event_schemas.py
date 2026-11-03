import pytest
from pydantic import ValidationError

from app.events.schemas import PAYLOADS, FeedbackReaction, validate_payload


def test_valid_payload_is_parsed() -> None:
    payload = validate_payload("feedback_reaction", {"feedback_id": 7, "understood": True})
    assert payload == FeedbackReaction(feedback_id=7, understood=True)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_payload("feedback_reaction", {"feedback_id": 7, "understood": True, "x": 1})


def test_unknown_type_or_version_is_rejected() -> None:
    with pytest.raises(KeyError):
        validate_payload("no_such_event", {})
    with pytest.raises(KeyError):
        validate_payload("feedback_reaction", {}, version=99)


def test_every_hypothesis_has_an_event_type() -> None:
    types = {event_type for event_type, _ in PAYLOADS}
    # H1/H3 testler, H5 tepki, H6 NPS, H7 öneri ve seçim.
    assert {
        "fixed_test_answer",
        "feedback_reaction",
        "nps_submitted",
        "extra_activity_chosen",
    } <= types
