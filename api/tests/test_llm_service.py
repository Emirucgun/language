"""LLM kapısının veritabanı tarafı, sahte istemciyle (gerçek API çağrısı yok)."""

import os
import uuid
from collections.abc import Iterator

import pytest
from alembic.config import Config
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.feedback.llm_schema import WritingFeedback
from app.llm.client import LLMProviderError
from app.llm.service import (
    DailyLimitExceeded,
    Prompt,
    calls_today,
    generate_structured,
)
from app.llm.snapshot import save_snapshot
from tests import fakes

OK = WritingFeedback(is_correct=True, errors=[], hint_tr=None, correction=None)


class FakeClient(fakes.FakeClient):
    def __init__(self, parsed: BaseModel | None = OK, error: Exception | None = None) -> None:
        super().__init__(parsed, error)


@pytest.fixture
def session(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


def _user(session: Session) -> uuid.UUID:
    return session.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes, interests) "
            "VALUES (:e, 'travel', 15, '{food,football}') RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@test.example"},
    ).scalar_one()


def _prompt(task: str = "Task: x\nLearner: I work as teacher.") -> Prompt:
    return Prompt(purpose="feedback", prompt_version="v1", static_block="static", task=task)


def test_successful_call_is_logged_with_cost(session: Session) -> None:
    user = _user(session)
    parsed, call = generate_structured(
        session, FakeClient(), prompt=_prompt(), output_type=WritingFeedback, user_id=user
    )
    assert parsed == OK
    assert call.status == "ok"
    assert call.provider == "anthropic"
    assert call.model == "claude-sonnet-5-5"
    assert call.cache_read_tokens == 900
    assert call.cost_microusd and call.cost_microusd > 0
    assert call.raw_on_failure is None


def test_unparsable_output_falls_back_and_keeps_raw_text(session: Session) -> None:
    user = _user(session)
    parsed, call = generate_structured(
        session,
        FakeClient(parsed=None),
        prompt=_prompt(),
        output_type=WritingFeedback,
        user_id=user,
    )
    assert parsed is None
    assert call.status == "invalid"
    assert call.raw_on_failure


def test_api_error_does_not_raise(session: Session) -> None:
    user = _user(session)
    error = LLMProviderError("APIConnectionError: bağlantı yok")
    parsed, call = generate_structured(
        session,
        FakeClient(error=error),
        prompt=_prompt(),
        output_type=WritingFeedback,
        user_id=user,
    )
    assert parsed is None
    assert call.status == "error"


def test_daily_limit_is_enforced(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_daily_call_limit_per_user", 2)
    user = _user(session)
    client = FakeClient()
    for _ in range(2):
        generate_structured(
            session, client, prompt=_prompt(), output_type=WritingFeedback, user_id=user
        )
    assert calls_today(session, user) == 2
    with pytest.raises(DailyLimitExceeded):
        generate_structured(
            session, client, prompt=_prompt(), output_type=WritingFeedback, user_id=user
        )
    assert len(client.requests) == 2


def test_email_never_reaches_the_model(session: Session) -> None:
    client = FakeClient()
    parsed, call = generate_structured(
        session,
        client,
        prompt=_prompt("Learner: my mail is ali@example.com"),
        output_type=WritingFeedback,
        user_id=_user(session),
    )
    assert client.requests == []
    assert parsed is None  # çağıran yedek yola geçer; istek çökmez
    assert call.status == "error"
    assert call.raw_on_failure == "personal_data"  # adresin kendisi kayda girmez


def test_snapshot_is_saved_once_and_has_no_identity(session: Session) -> None:
    user = _user(session)
    first = save_snapshot(session, user)
    second = save_snapshot(session, user)
    assert first.id == second.id
    assert "Interests: food, football" in first.text
    assert "@" not in first.text
