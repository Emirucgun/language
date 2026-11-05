"""Müfredat ajanı: kural katmanı, ret → geri bildirimle tekrar → yedek plan, hafta sırası."""

import os
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.curriculum.models import Curriculum
from app.curriculum.rules import (
    WEEKS,
    PoolItem,
    default_weights,
    fallback,
    validate,
    weekly_capacity,
)
from app.curriculum.schemas import CurriculumDraft, SkillWeights, WeekDraft
from app.curriculum.service import ensure_curriculum, new_item_order, view
from app.events.models import Event
from app.llm.client import LLMRequest, LLMResult
from app.llm.pricing import Usage
from app.scheduler.quotas import daily_quota
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401
from tests.test_session import item_ids  # noqa: F401 - havuzda öğe olsun

W = SkillWeights(vocabulary=0.4, reading=0.2, listening=0.2, writing=0.2)
POOL = [PoolItem(i, f"w{i}", f"k{i}", "A1") for i in range(1, 21)]


def _draft(weeks: list[list[int]], weights: SkillWeights = W) -> CurriculumDraft:
    return CurriculumDraft(
        summary_tr="Plan.",
        weeks=[
            WeekDraft(
                week=n,
                focus_tr=f"Hafta {n}",
                item_ids=ids,
                can_do_tr=["Yapabilirim."],
                skill_weights=weights,
            )
            for n, ids in enumerate(weeks, start=1)
        ],
    )


def _even(ids: list[int]) -> list[list[int]]:
    return [ids[i::WEEKS] for i in range(WEEKS)]


# --- Kural katmanı -------------------------------------------------------------


def test_valid_plan_passes_and_weights_are_normalized() -> None:
    skewed = SkillWeights(vocabulary=0.8, reading=0.4, listening=0.4, writing=0.4)
    result, fixed = validate(_draft(_even([p.id for p in POOL]), skewed), POOL, capacity=6)
    assert result.ok
    assert abs(sum(fixed.weeks[0].skill_weights.model_dump().values()) - 1) < 0.02


@pytest.mark.parametrize(
    ("weeks", "code"),
    [
        (_even([p.id for p in POOL])[:7], "weeks"),
        ([[999], *_even([p.id for p in POOL])[1:]], "unknown_items"),
        ([[1, 2], [2, 3], *_even(list(range(4, 21)))[2:]], "repeated_items"),
        ([list(range(1, 21)), [], [], [], [], [], [], []], "too_many_items"),
        ([[1], [], [], [], [], [], [], []], "low_coverage"),
    ],
)
def test_rule_violations_are_rejected(weeks: list[list[int]], code: str) -> None:
    result, _ = validate(_draft(weeks), POOL, capacity=6)
    assert code in {i.code for i in result.issues}


def test_english_grammar_jargon_in_turkish_text_is_rejected() -> None:
    draft = _draft(_even([p.id for p in POOL]))
    draft.summary_tr = "Yazma ve article hatalarına daha çok yer verdim."
    result, _ = validate(draft, POOL, capacity=6)
    assert [i.code for i in result.issues] == ["english_jargon"]
    assert "article" in result.issues[0].detail

    draft.summary_tr = "Artikel hatalarına ve “every day” kalıbına daha çok yer verdim."
    result, _ = validate(draft, POOL, capacity=6)
    assert result.ok


def test_fallback_always_satisfies_the_rules() -> None:
    weights = default_weights("daily_conversation", ["listening"])
    assert abs(sum(weights.model_dump().values()) - 1) < 0.02
    plan = fallback(POOL, capacity=6, weights=weights)
    result, _ = validate(plan, POOL, capacity=6)
    assert result.ok and len(plan.weeks) == WEEKS


# --- Ajan döngüsü (sahte LLM) ---------------------------------------------------


class Planner:
    """Görevdeki havuzu okuyup plan döndürür; `bad_first` ise ilk planı bilerek bozar."""

    def __init__(self, bad_first: int = 0) -> None:
        self.bad_first = bad_first
        self.tasks: list[str] = []

    def complete(self, request: LLMRequest) -> LLMResult:
        self.tasks.append(request.task)
        ids = [int(m) for m in re.findall(r"^(\d+) \|", request.task, flags=re.M)]
        capacity = int(re.search(r"capacity[^:]*: (\d+)", request.task).group(1))  # type: ignore[union-attr]
        weeks = [ids[i * capacity : (i + 1) * capacity] for i in range(WEEKS)]
        if len(self.tasks) <= self.bad_first:
            weeks[0] = [*weeks[0], 999_999]  # havuzda olmayan öğe
        plan = _draft(weeks)
        return LLMResult(request.config.model, plan, Usage(500, 900), "end_turn", 5000, None)


@pytest.fixture
def db(migrated_db: Config, item_ids: list[int]) -> Iterator[Session]:
    eng = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(eng) as s:
        yield s
        s.rollback()
    eng.dispose()


def _user(db: Session) -> User:
    user_id = db.execute(
        text(
            "INSERT INTO learning.users (email, goal, daily_minutes) "
            "VALUES (:e, 'travel', 15) RETURNING id"
        ),
        {"e": f"{uuid.uuid4()}@example.com"},
    ).scalar_one()
    return db.get_one(User, user_id)


def _events(db: Session, user: User) -> list[str]:
    return list(db.scalars(select(Event.type).where(Event.user_id == user.id)))


def test_agent_plan_is_stored_once(db: Session) -> None:
    user, planner = _user(db), Planner()
    curriculum = ensure_curriculum(db, planner, user)
    assert curriculum.version == 1 and curriculum.skill_weights["source"] == "agent"
    assert len(curriculum.weeks) == WEEKS
    assert ensure_curriculum(db, planner, user).id == curriculum.id
    assert len(planner.tasks) == 1
    assert _events(db, user) == ["curriculum_created"]


def test_rejected_plan_gets_the_reasons_and_one_more_try(db: Session) -> None:
    user, planner = _user(db), Planner(bad_first=1)
    curriculum = ensure_curriculum(db, planner, user)
    assert len(planner.tasks) == 2
    assert "rejected for these reasons" in planner.tasks[1] and "unknown_items" in planner.tasks[1]
    assert curriculum.skill_weights["source"] == "agent"


def test_two_rejections_fall_back_to_the_rule_plan(db: Session) -> None:
    user, planner = _user(db), Planner(bad_first=2)
    curriculum = ensure_curriculum(db, planner, user)
    assert len(planner.tasks) == 2 and curriculum.skill_weights["source"] == "fallback"
    assert curriculum.llm_call_id is None


def test_replanning_creates_a_new_version(db: Session) -> None:
    user = _user(db)
    ensure_curriculum(db, Planner(), user)
    second = ensure_curriculum(db, Planner(), user, reason="weekly")
    assert second.version == 2 and second.change_reason == "weekly"
    assert _events(db, user) == ["curriculum_created", "curriculum_replanned"]
    assert db.scalar(
        select(Curriculum).where(Curriculum.user_id == user.id, Curriculum.version == 1)
    )


def test_replan_moves_the_shown_week_forward_but_not_the_item_order(
    db: Session, item_ids: list[int]
) -> None:
    """Yeniden plan yeni bir 8 hafta üretir: sıra planın 1. haftasından, gösterim ilerler."""
    user = _user(db)
    ensure_curriculum(db, Planner(), user)
    replanned = ensure_curriculum(db, Planner(), user, reason="weekly_review")

    shown = view(db, replanned)
    assert shown.current_week == 2
    assert [w.week for w in shown.weeks] == list(range(2, 2 + WEEKS))
    assert [w.week for w in shown.weeks if w.current] == [2]
    assert (
        new_item_order(replanned)[: len(replanned.weeks[0]["item_ids"])]
        == (replanned.weeks[0]["item_ids"])
    )


@pytest.mark.parametrize(("minutes", "per_week"), [(10, 12), (15, 18), (30, 24)])
def test_large_pool_fits_every_daily_time(minutes: int, per_week: int) -> None:
    pool = [PoolItem(i, f"w{i}", f"k{i}", "A1") for i in range(1, 201)]
    capacity = weekly_capacity(daily_quota(minutes).max_new)
    assert capacity == per_week

    plan = fallback(pool, capacity, W)
    result, _ = validate(plan, pool, capacity)
    assert result.ok, result.issues
    assert sum(len(w.item_ids) for w in plan.weeks) == capacity * WEEKS

    # Kapasitenin %80'i yeterli, altı reddedilir: havuzun %80'i (160) istenmez.
    enough = -(-capacity * WEEKS * 8 // 10) // WEEKS + 1
    ids = [p.id for p in pool]
    passing = _draft([ids[n * enough : (n + 1) * enough] for n in range(WEEKS)])
    assert validate(passing, pool, capacity)[0].ok

    short = capacity * 7 // 10
    failing = _draft([ids[n * short : (n + 1) * short] for n in range(WEEKS)])
    assert "low_coverage" in {i.code for i in validate(failing, pool, capacity)[0].issues}


def test_quota_is_the_single_source_for_plan_and_session() -> None:
    assert [daily_quota(m).max_new for m in (5, 10, 15, 20, 30, None)] == [2, 2, 3, 3, 4, 3]
    assert [daily_quota(m).max_reviews for m in (10, 15, 30)] == [4, 6, 8]


def test_new_item_order_starts_at_the_current_week() -> None:
    created = datetime(2026, 11, 2, tzinfo=UTC)
    curriculum = Curriculum(
        weeks=[{"week": n, "item_ids": [n * 10, n * 10 + 1]} for n in range(1, WEEKS + 1)],
        created_at=created,
    )
    assert new_item_order(curriculum, created + timedelta(days=1))[:2] == [10, 11]
    third_week = new_item_order(curriculum, created + timedelta(days=15))
    assert third_week[:2] == [30, 31] and third_week[-2:] == [20, 21]  # kaçırılanlar sonda


def test_curriculum_endpoint_falls_back_without_a_usable_llm(
    client: TestClient,
    sender: FakeSender,
    engine: object,
) -> None:
    _login(client, sender, engine)
    _consent(client)
    r = client.get("/api/curriculum")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["weeks"]) == WEEKS and body["current_week"] == 1
    assert body["weeks"][0]["current"] is True and "tahmin" in body["estimate_tr"]
