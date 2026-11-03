"""Yerleştirme testi: puanlama, soru bankası, HTTP akışı ve seviyenin oturuma etkisi."""

import json
import os
import uuid
from datetime import date

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth.models import User
from app.onboarding.placement import FixedQuestion, score
from app.sessions.generation import plan_session
from scripts.placement_v1 import QUESTIONS
from tests.conftest import _libpq_url
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401

BANK = [FixedQuestion.model_validate(q) for q in QUESTIONS]
A1 = [q for q in BANK if q.level == "A1"]
A2 = [q for q in BANK if q.level == "A2"]


def _answers(a1_right: int, a2_right: int) -> dict[str, str]:
    answers = {q.id: q.answer for q in A1[:a1_right]}
    answers |= {q.id: q.answer for q in A2[:a2_right]}
    return answers


# --- Puanlama ve soru bankası ---------------------------------------------------


def test_question_bank_is_well_formed() -> None:
    assert len({q.id for q in BANK}) == len(BANK) == 24
    assert len(A1) == len(A2) == 12
    for q in BANK:
        assert q.options.count(q.answer) == 1, q.id
        assert len(set(q.options)) == len(q.options), q.id


@pytest.mark.parametrize(
    ("a1", "a2", "estimate", "sublevel"),
    [
        (0, 0, "pre-A1", 1),
        (5, 12, "pre-A1", 1),  # A1 temeli yoksa A2 doğruları şans sayılır
        (6, 0, "A1", 1),
        (10, 5, "A1", 2),
        (12, 6, "A2", 1),
        (12, 10, "A2", 2),
    ],
)
def test_scoring_rules(a1: int, a2: int, estimate: str, sublevel: int) -> None:
    result = score(BANK, _answers(a1, a2))
    assert (result.cefr_estimate, result.sublevel) == (estimate, sublevel)


def test_options_are_shuffled_per_learner_but_stable() -> None:
    from app.onboarding.fixed_tests import views

    first, second = uuid.uuid4(), uuid.uuid4()
    mine = views(BANK, first)
    assert [v.options for v in mine] == [v.options for v in views(BANK, first)]  # devamda aynı
    assert [v.options for v in mine] != [v.options for v in views(BANK, second)]
    # Doğru cevap hep ilk şık olmasın (kaydedilen bankada çoğu ilk sırada).
    first_is_answer = sum(v.options[0] == q.answer for v, q in zip(mine, BANK, strict=True))
    assert first_is_answer < len(BANK) / 2


def test_dont_know_counts_as_wrong() -> None:
    answers = {q.id: "" for q in BANK}
    assert score(BANK, answers).score == 0


# --- HTTP akışı -----------------------------------------------------------------


@pytest.fixture(scope="module")
def placement_test(migrated_db: Config) -> None:
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        conn.execute(
            "INSERT INTO content.fixed_tests (purpose, version, questions) "
            "VALUES ('placement', 1, %s::jsonb) ON CONFLICT DO NOTHING",
            (json.dumps([q.model_dump() for q in BANK]),),
        )


@pytest.mark.usefixtures("placement_test")
def test_placement_flow(client: TestClient, sender: FakeSender, engine: object) -> None:  # noqa: F811
    _login(client, sender, engine)
    _consent(client)
    assert client.get("/api/auth/me").json()["placement_done"] is False

    view = client.get("/api/onboarding/placement").json()
    assert len(view["questions"]) == 24 and view["result"] is None
    assert "answer" not in view["questions"][0]  # cevap öğrenciye gitmez

    for q in A1:
        r = client.post(
            "/api/onboarding/placement/answer", json={"question_id": q.id, "answer": q.answer}
        )
        assert r.status_code == 204
    again = client.post(
        "/api/onboarding/placement/answer", json={"question_id": A1[0].id, "answer": "x"}
    )
    assert again.status_code == 409
    unknown = client.post(
        "/api/onboarding/placement/answer", json={"question_id": "nope", "answer": "x"}
    )
    assert unknown.status_code == 404

    result = client.post("/api/onboarding/placement/complete").json()
    assert result["cefr_estimate"] == "A1" and result["sublevel"] == 2
    # Tekrar tamamlama aynı sonucu döner; tamamlanmış teste cevap eklenemez.
    assert client.post("/api/onboarding/placement/complete").json() == result
    late = client.post(
        "/api/onboarding/placement/answer", json={"question_id": A2[0].id, "answer": "x"}
    )
    assert late.status_code == 409

    me = client.get("/api/auth/me").json()
    assert me["placement_done"] is True and me["level"] == "A1"


# --- Seviye oturumu nasıl etkiler ------------------------------------------------


@pytest.mark.usefixtures("placement_test")
def test_a2_learner_gets_a2_items_first(migrated_db: Config) -> None:
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        a2_item = conn.execute(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, sublevel) "
            "VALUES ('test', 'word', 'passport', 'pasaport', 'A2', -1) RETURNING id"
        ).fetchone()
        test_id = conn.execute(
            "SELECT id FROM content.fixed_tests WHERE purpose = 'placement' AND version = 1"
        ).fetchone()
    assert a2_item and test_id

    engine_ = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine_) as db:
        user_id = db.execute(
            text("INSERT INTO learning.users (email, goal) VALUES (:e, 'work') RETURNING id"),
            {"e": f"{uuid.uuid4()}@example.com"},
        ).scalar_one()
        user = db.get_one(User, user_id)
        a1_plan = plan_session(db, user, date(2026, 11, 9))
        assert a2_item[0] not in [c.id for c in a1_plan.new]  # A1 öğrencisine A2 öğesi yok
        assert a1_plan.cefr_sub == "A1.1"

        db.execute(
            text(
                "INSERT INTO learning.events (user_id, type, occurred_at, payload) VALUES "
                "(:u, 'fixed_test_completed', now(), CAST(:p AS jsonb))"
            ),
            {
                "u": user_id,
                "p": json.dumps(
                    {"test_id": test_id[0], "score": 0.9, "cefr_estimate": "A2", "sublevel": 2}
                ),
            },
        )
        a2_plan = plan_session(db, user, date(2026, 11, 9))
        assert a2_plan.new[0].id == a2_item[0] and a2_plan.cefr_sub == "A2.2"
        db.rollback()
    engine_.dispose()
