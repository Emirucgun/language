"""Tekrar motorunun veritabanı tarafı: uygulama rolüyle, test veritabanında."""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.scheduler.service import (
    find_mismatches,
    rebuild_item_states,
    select_items,
    update_item_states,
)
from tests.conftest import _libpq_url


@pytest.fixture
def items(migrated_db: Config) -> list[int]:
    # İçerik şeması uygulama rolüne kapalı; öğeleri sahip rolü ekler ve commit eder.
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        rows = conn.execute(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr) "
            "SELECT 'test', 'word', 'w' || g, 'k' || g, 'A1' FROM generate_series(1, 6) g "
            "RETURNING id"
        ).fetchall()
    return [r[0] for r in rows]


@pytest.fixture
def session(migrated_db: Config) -> Iterator[Session]:
    engine = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine) as s:
        yield s
        s.rollback()
    engine.dispose()


def _user(session: Session) -> uuid.UUID:
    return session.execute(
        text("INSERT INTO learning.users (email) VALUES (:e) RETURNING id"),
        {"e": f"{uuid.uuid4()}@test"},
    ).scalar_one()


def _rate(session: Session, user_id: uuid.UUID, item_id: int, rating: int) -> None:
    session.execute(
        text(
            "INSERT INTO learning.events (user_id, type, occurred_at, item_id, rating) "
            "VALUES (:u, 'answer_submitted', now(), :i, :r)"
        ),
        {"u": user_id, "i": item_id, "r": rating},
    )


def test_incremental_updates_match_replay(session: Session, items: list[int]) -> None:
    user = _user(session)
    a, b, c = items[:3]

    _rate(session, user, a, 3)
    _rate(session, user, b, 1)
    assert update_item_states(session, user) == 2

    _rate(session, user, a, 3)
    _rate(session, user, c, 3)
    assert update_item_states(session, user) == 2
    # Yeni olay yoksa hiçbir şey değişmez.
    assert update_item_states(session, user) == 0

    assert find_mismatches(session, user) == []


def test_rebuild_repairs_a_corrupted_state(session: Session, items: list[int]) -> None:
    user = _user(session)
    _rate(session, user, items[0], 3)
    update_item_states(session, user)

    session.execute(
        text("UPDATE learning.item_states SET stability = 999 WHERE user_id = :u"), {"u": user}
    )
    assert find_mismatches(session, user) == [items[0]]

    rebuild_item_states(session, user)
    assert find_mismatches(session, user) == []


def test_select_items_prefers_due_reviews_and_skips_seen_new_items(
    session: Session, items: list[int]
) -> None:
    user = _user(session)
    learned, forgotten, *fresh = items
    _rate(session, user, learned, 3)
    _rate(session, user, forgotten, 1)
    update_item_states(session, user)

    tomorrow = datetime.now(UTC) + timedelta(days=1)
    selection = select_items(
        session,
        user,
        due_before=tomorrow,
        candidate_new_ids=[learned, *fresh],
        max_reviews=10,
        max_new=2,
    )
    assert forgotten in selection.review_item_ids
    assert learned not in selection.new_item_ids
    assert selection.new_item_ids == fresh[:2]


def test_review_backlog_halves_new_items(session: Session, items: list[int]) -> None:
    user = _user(session)
    for item in items[:3]:
        _rate(session, user, item, 1)
    update_item_states(session, user)

    selection = select_items(
        session,
        user,
        due_before=datetime.now(UTC) + timedelta(days=1),
        candidate_new_ids=items[3:],
        max_reviews=2,
        max_new=2,
    )
    assert len(selection.review_item_ids) == 2
    assert len(selection.new_item_ids) == 1
