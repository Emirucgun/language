"""Ölçüm testleri: iki form (H3), 14 gün hatırlama testi (H1) ve analiz."""

import asyncio
import json
import os
import uuid
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from procrastinate.testing import InMemoryConnector
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from analysis.hypotheses import (
    PRE_POST_SQL,
    RETENTION_SQL,
    PrePost,
    RetentionAnswer,
    h1,
    h3,
    sign_test,
)
from app import jobs
from app.assessment import retention
from app.assessment.scheduling import users_needing_retention_test
from app.content.models import Item
from app.llm.snapshot import gather_facts
from app.onboarding import fixed_tests
from app.onboarding.placement import FixedQuestion, score
from app.scheduler.retention import CONTROLS, MAX_TARGETS, Studied, eligible
from scripts.placement_form_b import QUESTIONS as FORM_B_QUESTIONS
from scripts.placement_v1 import QUESTIONS as FORM_A_QUESTIONS
from tests.conftest import _libpq_url
from tests.test_api import FakeSender, _consent, _login, client, engine, sender  # noqa: F401

FORM_A = [FixedQuestion.model_validate(q) for q in FORM_A_QUESTIONS]
FORM_B = [FixedQuestion.model_validate(q) for q in FORM_B_QUESTIONS]
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def _item(
    item_id: int = 1,
    text_en: str = "bread",
    sentences: list[dict[str, str]] | None = None,
    kind: str = "word",
    forms: list[str] | None = None,
) -> Item:
    return Item(
        id=item_id,
        kind=kind,
        cefr="A1",
        text_en=text_en,
        text_tr="ekmek",
        forms=forms or [],
        reference_sentences=sentences or [],
    )


SENTENCE = {"en": "I eat bread every day.", "tr": "Her gün ekmek yerim."}
OTHERS = [_item(i, word) for i, word in enumerate(("milk", "water", "apple", "rice"), start=2)]


# --- Formlar --------------------------------------------------------------------


def test_forms_are_parallel_and_share_no_question() -> None:
    def shape(bank: list[FixedQuestion]) -> Counter[tuple[str, str]]:
        return Counter((q.section, q.level) for q in bank)

    assert shape(FORM_A) == shape(FORM_B)
    assert not {q.id for q in FORM_A} & {q.id for q in FORM_B}
    assert not {q.prompt for q in FORM_A} & {q.prompt for q in FORM_B}
    assert not {q.passage for q in FORM_A if q.passage} & {q.passage for q in FORM_B if q.passage}
    for q in FORM_B:
        assert q.options.count(q.answer) == 1, q.id
        assert len(set(q.options)) == len(q.options), q.id


def test_both_forms_use_the_same_scoring() -> None:
    for bank in (FORM_A, FORM_B):
        a1_only = {q.id: q.answer for q in bank if q.level == "A1"}
        assert score(bank, a1_only).cefr_estimate == "A1"
        assert score(bank, a1_only).sublevel == 2
        assert score(bank, {q.id: q.answer for q in bank}).cefr_estimate == "A2"
        assert score(bank, {}).cefr_estimate == "pre-A1"


@pytest.fixture(scope="module")
def forms(migrated_db: Config) -> Iterator[None]:
    """B formu modül sonunda kalkar: diğer testler tek formlu yerleştirmeyi varsayar."""
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        for form, bank in (("A", FORM_A), ("B", FORM_B)):
            conn.execute(
                "INSERT INTO content.fixed_tests (purpose, form, version, questions) "
                "VALUES ('placement', %s, 1, %s::jsonb) ON CONFLICT DO NOTHING",
                (form, json.dumps([q.model_dump() for q in bank])),
            )
        conn.commit()
        yield
        conn.execute("DELETE FROM content.fixed_tests WHERE form = 'B'")
        conn.commit()


@pytest.fixture
def db(migrated_db: Config) -> Iterator[Session]:
    engine_ = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    with Session(engine_) as s:
        yield s
        s.rollback()
    engine_.dispose()


def _user(db: Session, user_id: uuid.UUID | None = None) -> uuid.UUID:
    return db.execute(
        text(
            "INSERT INTO learning.users (id, email, consent_at, is_adult_confirmed) "
            "VALUES (:i, :e, now(), true) RETURNING id"
        ),
        {"i": user_id or uuid.uuid4(), "e": f"{uuid.uuid4()}@example.com"},
    ).scalar_one()


def _take(db: Session, user_id: uuid.UUID, phase: fixed_tests.Phase, right: bool = True) -> None:
    current = fixed_tests.state(db, user_id, phase)
    for q in current.questions:
        fixed_tests.answer(db, user_id, phase, q.id, q.answer if right else "", None)
    fixed_tests.complete(db, user_id, phase)


@pytest.mark.usefixtures("forms")
def test_learners_are_split_across_forms_and_keep_their_form(db: Session) -> None:
    even = _user(db, uuid.UUID(int=2 + (uuid.uuid4().int >> 2 << 2)))
    odd = _user(db, uuid.UUID(int=1 + (uuid.uuid4().int >> 2 << 2)))
    assert fixed_tests.phase_test(db, even, "pre").form == "A"
    assert fixed_tests.phase_test(db, odd, "pre").form == "B"


@pytest.mark.usefixtures("forms")
def test_post_test_is_always_the_other_form(db: Session) -> None:
    for parity in (0, 1):
        user_id = _user(db, uuid.UUID(int=parity + (uuid.uuid4().int >> 2 << 2)))
        _take(db, user_id, "pre")
        pre = fixed_tests.phase_test(db, user_id, "pre")
        post = fixed_tests.phase_test(db, user_id, "post")
        assert pre.form != post.form

        _take(db, user_id, "post", right=False)
        assert fixed_tests.phase_test(db, user_id, "post").id == post.id
        assert fixed_tests.phase_test(db, user_id, "pre").id == pre.id


@pytest.mark.usefixtures("forms")
def test_a_started_test_survives_a_new_version(db: Session) -> None:
    user_id = _user(db)
    first = fixed_tests.state(db, user_id, "pre")
    fixed_tests.answer(db, user_id, "pre", first.questions[0].id, "x", None)
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        newer = conn.execute(
            "INSERT INTO content.fixed_tests (purpose, form, version, questions) "
            "SELECT purpose, form, version + 100, questions FROM content.fixed_tests "
            "WHERE id = %s RETURNING id",
            (first.test.id,),
        ).fetchone()
        assert newer is not None
        conn.commit()
        try:
            assert fixed_tests.current_test(db, first.test.form).id == newer[0]
            current = fixed_tests.state(db, user_id, "pre")
            assert current.test.id == first.test.id
            assert current.answered == {first.questions[0].id}
        finally:
            conn.execute("DELETE FROM content.fixed_tests WHERE id = %s", (newer[0],))
            conn.commit()


@pytest.mark.usefixtures("forms")
def test_post_result_does_not_change_the_level(db: Session) -> None:
    user_id = _user(db)
    _take(db, user_id, "pre", right=False)
    assert fixed_tests.user_level(db, user_id) == ("A1", "A1.1")
    _take(db, user_id, "post", right=True)

    placement = fixed_tests.placement_result(db, user_id)
    assert placement is not None and placement.cefr_estimate == "pre-A1"
    assert fixed_tests.user_level(db, user_id) == ("A1", "A1.1")
    assert gather_facts(db, user_id).level == "pre-A1"  # LLM özeti de eski seviyeyi görür


@pytest.mark.usefixtures("forms")
def test_post_test_opens_after_eight_weeks_and_closes_when_done(db: Session) -> None:
    user_id = _user(db)
    assert fixed_tests.post_open(db, user_id) is False
    _take(db, user_id, "pre")
    assert fixed_tests.post_due(db, user_id) is False
    later = datetime.now(UTC) + timedelta(days=fixed_tests.POST_TEST_DAYS, minutes=1)
    assert fixed_tests.post_due(db, user_id, later) is True
    _take(db, user_id, "post")
    assert fixed_tests.post_due(db, user_id, later) is False


@pytest.mark.usefixtures("forms")
def test_post_test_http_flow(
    client: TestClient,
    sender: FakeSender,
    engine: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _login(client, sender, engine)
    _consent(client)
    view = client.get("/api/onboarding/placement").json()
    for q in view["questions"]:
        r = client.post(
            "/api/onboarding/placement/answer", json={"question_id": q["id"], "answer": ""}
        )
        assert r.status_code == 204
    assert client.post("/api/onboarding/placement/complete").status_code == 200

    assert client.get("/api/tests/due").json() == {"retention": False, "post": False}
    early = client.post("/api/tests/post/answer", json={"question_id": "x", "answer": "y"})
    assert client.get("/api/tests/post").status_code == 409 and early.status_code == 409

    # Olaylar değiştirilemez; sekiz hafta sınırı yukarıda `post_open` ile sınanıyor.
    monkeypatch.setattr(fixed_tests, "post_open", lambda db, user_id, now=None: True)
    post = client.get("/api/tests/post").json()
    pre_ids = {q["id"] for q in view["questions"]}
    assert not pre_ids & {q["id"] for q in post["questions"]}
    assert "answer" not in post["questions"][0]
    for q in post["questions"]:
        r = client.post("/api/tests/post/answer", json={"question_id": q["id"], "answer": ""})
        assert r.status_code == 204
    result = client.post("/api/tests/post/complete").json()
    assert result == {"score": 0.0, "pre_score": 0.0}
    assert client.get("/api/tests/post").json()["result"] == result
    assert client.get("/api/auth/me").json()["level"] == "pre-A1"


# --- Hatırlama testi: kurallar --------------------------------------------------


def _studied(item_id: int, first_days: int, last_days: int) -> Studied:
    return Studied(item_id, NOW - timedelta(days=first_days), NOW - timedelta(days=last_days))


def test_eligibility_window() -> None:
    rows = [
        _studied(1, 14, 14),  # tam 14 gün
        _studied(2, 13, 13),  # erken
        _studied(3, 20, 3),  # son tekrar üç gün önce: dinlenmiş
        _studied(4, 20, 1),  # dün tekrar edildi: taze hatıra
        _studied(5, 28, 10),  # sınırda
        _studied(6, 29, 10),  # çok eski
        _studied(7, 20, 10),  # daha önce test edildi
    ]
    assert [s.item_id for s in eligible(rows, {7}, NOW)] == [1, 3, 5]


def test_cloze_blanks_the_base_form_only() -> None:
    assert retention.cloze(_item(sentences=[SENTENCE])) == (
        "I eat ___ every day.",
        "Her gün ekmek yerim.",
    )
    capital = {"en": "Bread is cheap.", "tr": "Ekmek ucuzdur."}
    assert retention.cloze(_item(sentences=[capital])) == ("___ is cheap.", "Ekmek ucuzdur.")

    inflected = {"en": "She goes to work.", "tr": "İşe gider."}
    assert retention.cloze(_item(text_en="go", sentences=[inflected])) is None
    both = [inflected, {"en": "I go to work.", "tr": "İşe giderim."}]
    assert retention.cloze(_item(text_en="go", sentences=both)) == (
        "I ___ to work.",
        "İşe giderim.",
    )
    part = {"en": "They eat breadsticks.", "tr": "Grissini yerler."}
    assert retention.cloze(_item(sentences=[part])) is None
    assert retention.cloze(_item()) is None


def test_question_has_four_stable_options_from_the_same_kind() -> None:
    user_id = uuid.uuid4()
    item = _item(sentences=[SENTENCE])
    chunk = _item(9, "go home", kind="chunk")
    pool = [item, chunk, *OTHERS]
    question = retention.question_for(item, pool, user_id, "target", NOW)
    assert question is not None
    assert len(question.options) == len(set(question.options)) == 4
    assert question.answer == "bread" and "bread" in question.options
    assert "go home" not in question.options
    assert retention.question_for(item, pool, user_id, "target", NOW) == question


def test_no_question_without_enough_distractors() -> None:
    item = _item(sentences=[SENTENCE])
    assert retention.question_for(item, [item, *OTHERS[:2]], uuid.uuid4(), "target") is None


def test_distractors_exclude_forms_and_words_of_the_sentence() -> None:
    sentence = {"en": "I drink milk and eat bread.", "tr": "Süt içer, ekmek yerim."}
    item = _item(sentences=[sentence], forms=["breads"])
    pool = [item, _item(20, "breads"), *OTHERS, _item(21, "pear")]
    question = retention.question_for(item, pool, uuid.uuid4(), "target")
    assert question is not None
    assert "breads" not in question.options and "milk" not in question.options


# --- Hatırlama testi: akış ------------------------------------------------------

TARGETS = 8


@pytest.fixture(scope="module")
def pool(migrated_db: Config) -> Iterator[list[int]]:
    """Silinmez, pasifleşir: olaylar öğelere bağlı kalır."""
    with psycopg.connect(_libpq_url("TEST_DATABASE_URL")) as conn:
        ids = []
        for n in range(TARGETS + CONTROLS + 3):
            word = f"zword{n}"
            row = conn.execute(
                "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, "
                "reference_sentences) VALUES ('retention-test', 'word', %s, %s, 'A1', %s::jsonb) "
                "RETURNING id",
                (word, f"kelime{n}", json.dumps([{"en": f"I see {word} here.", "tr": "Görürüm."}])),
            ).fetchone()
            assert row is not None
            ids.append(int(row[0]))
        conn.commit()
        yield ids
        conn.execute("UPDATE content.items SET active = false WHERE id = ANY(%s)", (ids,))
        conn.commit()


def _study(db: Session, user_id: uuid.UUID, items: list[int], days: int = 15) -> None:
    for item_id in items:
        db.execute(
            text(
                "INSERT INTO learning.events (user_id, type, item_id, rating, occurred_at, payload)"
                " VALUES (:u, 'answer_submitted', :i, 3, now() - make_interval(days => :d), "
                "CAST(:p AS jsonb))"
            ),
            {
                "u": user_id,
                "i": item_id,
                "d": days,
                "p": json.dumps({"question": 0, "answer": "x", "correct": True}),
            },
        )


def _questions(db: Session, user_id: uuid.UUID) -> list[retention.RetentionQuestion]:
    test = retention.open_test(db, user_id)
    assert test is not None
    return test.questions


def test_test_has_targets_and_unstudied_controls(db: Session, pool: list[int]) -> None:
    user_id = _user(db)
    targets = pool[:TARGETS]
    _study(db, user_id, targets)
    assert retention.create_test(db, user_id) is not None

    questions = _questions(db, user_id)
    assert {q.item_id for q in questions if q.group == "target"} == set(targets)
    controls = [q for q in questions if q.group == "control"]
    assert len(controls) == CONTROLS
    assert not {q.item_id for q in controls} & set(targets)
    assert all(q.first_studied is None for q in controls)
    assert len(questions) <= MAX_TARGETS + CONTROLS


def test_too_few_items_opens_no_test(db: Session, pool: list[int]) -> None:
    user_id = _user(db)
    _study(db, user_id, pool[:4])
    assert retention.create_test(db, user_id) is None
    assert retention.open_test(db, user_id) is None


def test_recently_studied_items_stay_out(db: Session, pool: list[int]) -> None:
    user_id = _user(db)
    _study(db, user_id, pool[:TARGETS])
    _study(db, user_id, pool[:TARGETS], days=1)  # dün tekrar edildi
    assert retention.create_test(db, user_id) is None


def test_open_test_blocks_a_second_one_and_items_are_used_once(
    db: Session, pool: list[int]
) -> None:
    user_id = _user(db)
    _study(db, user_id, pool[:TARGETS])
    first = retention.create_test(db, user_id)
    assert first is not None
    assert retention.create_test(db, user_id) is None

    for q in _questions(db, user_id):
        retention.answer(db, user_id, q.id, q.answer, None)
    assert retention.open_test(db, user_id) is None
    assert retention.create_test(db, user_id) is None  # aynı öğeler bir daha girmez


def test_answers_touch_no_review_state_and_score_targets_separately(
    db: Session, pool: list[int]
) -> None:
    user_id = _user(db)
    _study(db, user_id, pool[:TARGETS])
    retention.create_test(db, user_id)
    questions = _questions(db, user_id)

    outcome = None
    for q in questions:
        right = q.group == "control" or q.item_id != pool[0]
        outcome = retention.answer(db, user_id, q.id, q.answer if right else "", None)
    assert outcome == retention.Score(TARGETS - 1, TARGETS, CONTROLS, CONTROLS)

    rows = db.execute(
        text(
            "SELECT item_id, rating, payload FROM learning.events "
            "WHERE user_id = :u AND type = 'retention_test_answer'"
        ),
        {"u": user_id},
    ).all()
    assert len(rows) == len(questions)
    assert all(r.item_id is None and r.rating is None for r in rows)
    target = next(r.payload for r in rows if r.payload["group"] == "target")
    assert target["days_since_study"] == 15
    assert (
        db.scalar(
            text(
                "SELECT count(*) FROM learning.events "
                "WHERE user_id = :u AND type = 'retention_test_completed'"
            ),
            {"u": user_id},
        )
        == 1
    )
    assert (
        db.scalar(
            text("SELECT count(*) FROM learning.item_states WHERE user_id = :u"), {"u": user_id}
        )
        == 0
    )


def test_answer_rules(db: Session, pool: list[int]) -> None:
    user_id = _user(db)
    with pytest.raises(retention.NoOpenTest):
        retention.answer(db, user_id, "q1", "x", None)
    _study(db, user_id, pool[:TARGETS])
    retention.create_test(db, user_id)
    question = _questions(db, user_id)[0]
    with pytest.raises(retention.QuestionNotFound):
        retention.answer(db, user_id, "nope", "x", None)
    retention.answer(db, user_id, question.id, "x", None)
    with pytest.raises(retention.AlreadyAnswered):
        retention.answer(db, user_id, question.id, "x", None)


def test_due_selection(db: Session, pool: list[int]) -> None:
    fresh, ready, waiting, recent = _user(db), _user(db), _user(db), _user(db)
    _study(db, fresh, pool[:TARGETS], days=3)
    for user_id in (ready, waiting, recent):
        _study(db, user_id, pool[:TARGETS])
    retention.create_test(db, waiting)  # açık test var
    retention.create_test(db, recent)
    for q in _questions(db, recent):  # bitti ama yeni: haftada bir
        retention.answer(db, recent, q.id, "", None)

    selected = set(users_needing_retention_test(db))
    assert ready in selected
    assert not selected & {fresh, waiting, recent}


def test_scheduler_queues_one_job_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    monkeypatch.setattr(jobs, "_due_retention_tests", lambda: [user_id])
    connector = InMemoryConnector()
    with jobs.app.replace_connector(connector):
        assert asyncio.run(jobs.schedule_retention_tests(timestamp=0)) == 1
        assert asyncio.run(jobs.schedule_retention_tests(timestamp=3600)) == 0
    queued = [j for j in connector.jobs.values() if j["task_name"] == "retention_test_due"]
    assert len(queued) == 1 and queued[0]["args"] == {"user_id": str(user_id)}


def test_job_and_http_flow(
    client: TestClient,
    sender: FakeSender,
    engine: object,
    pool: list[int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _login(client, sender, engine)
    _consent(client)
    user_id = uuid.UUID(client.get("/api/auth/me").json()["id"])
    assert client.get("/api/tests/retention").status_code == 404

    engine_ = create_engine(os.environ["TEST_APP_DATABASE_URL"])
    monkeypatch.setattr(jobs, "SessionLocal", sessionmaker(engine_, expire_on_commit=False))
    with Session(engine_) as s:
        _study(s, user_id, pool[:TARGETS])
        s.commit()
    assert jobs.retention_test_due(str(user_id)) is not None
    assert jobs.retention_test_due(str(user_id)) is None  # tekrar çalışması test açmaz
    engine_.dispose()

    assert client.get("/api/tests/due").json()["retention"] is True
    view = client.get("/api/tests/retention").json()
    assert len(view["questions"]) == TARGETS + CONTROLS and view["answered"] == []
    first = view["questions"][0]
    assert set(first) == {"id", "sentence_en", "sentence_tr", "options"}  # cevap ve grup yok
    assert "___" in first["sentence_en"]

    last = None
    for q in view["questions"]:
        last = client.post(
            "/api/tests/retention/answer", json={"question_id": q["id"], "answer": q["options"][0]}
        )
        assert last.status_code == 200
    assert last is not None
    done = last.json()
    assert done["done"] is True and done["total"] == TARGETS  # kontroller not sayılmaz
    assert client.get("/api/tests/due").json()["retention"] is False
    assert client.get("/api/tests/retention").status_code == 404


def test_analysis_queries_read_real_events(db: Session, pool: list[int]) -> None:
    user_id = _user(db)
    _study(db, user_id, pool[:TARGETS])
    retention.create_test(db, user_id)
    for q in _questions(db, user_id):
        retention.answer(db, user_id, q.id, q.answer, None)

    rows = [
        RetentionAnswer(*row)
        for row in db.execute(text(RETENTION_SQL)).all()
        if row[0] == str(user_id)
    ]
    assert h1(rows).target_total == TARGETS and h1(rows).control_total == CONTROLS


@pytest.mark.usefixtures("forms")
def test_analysis_pairs_pre_and_post(db: Session) -> None:
    user_id = _user(db)
    _take(db, user_id, "pre", right=False)
    _take(db, user_id, "post", right=True)
    pairs = [
        PrePost(*row) for row in db.execute(text(PRE_POST_SQL)).all() if row[0] == str(user_id)
    ]
    assert len(pairs) == 1
    assert pairs[0].gain == pytest.approx(1.0)
    assert pairs[0].pre_form == fixed_tests.phase_test(db, user_id, "pre").form


# --- Analiz ---------------------------------------------------------------------


def _answers(user: str, group: str, right: int, wrong: int) -> list[RetentionAnswer]:
    return [RetentionAnswer(user, group, True)] * right + [
        RetentionAnswer(user, group, False)
    ] * wrong


def test_h1_separates_target_from_baseline() -> None:
    result = h1(
        [
            *_answers("a", "target", 8, 2),
            *_answers("b", "target", 6, 4),
            *_answers("a", "control", 1, 2),
            *_answers("b", "control", 0, 3),
        ]
    )
    assert (result.target_correct, result.target_total) == (14, 20)
    assert result.target_rate == pytest.approx(0.7)
    assert result.control_rate == pytest.approx(1 / 6)
    assert result.net == pytest.approx(0.7 - 1 / 6)
    assert result.user_mean == pytest.approx(0.7)
    assert result.users == 2
    assert result.target_lower is not None and result.target_lower < 0.7


def test_h1_user_mean_is_not_dominated_by_one_learner() -> None:
    result = h1([*_answers("a", "target", 30, 0), *_answers("b", "target", 0, 2)])
    assert result.target_rate == pytest.approx(30 / 32)
    assert result.user_mean == pytest.approx(0.5)


def test_h1_without_data() -> None:
    result = h1([])
    assert result.target_rate is None and result.net is None and result.target_lower is None


def test_sign_test() -> None:
    assert sign_test(0, 0) == 1.0
    assert sign_test(5, 0) == pytest.approx(1 / 32)
    assert sign_test(1, 1) == pytest.approx(0.75)


def test_h3_reports_gain_by_first_form() -> None:
    result = h3(
        [
            PrePost("a", "A", 0.4, 0.6),
            PrePost("b", "A", 0.5, 0.7),
            PrePost("c", "B", 0.5, 0.5),
            PrePost("d", "B", 0.6, 0.5),
        ]
    )
    assert result.pairs == 4 and (result.improved, result.worsened) == (2, 1)
    assert result.mean_gain == pytest.approx(0.075)
    assert result.gain_by_first_form["A"] == pytest.approx(0.2)
    assert result.gain_by_first_form["B"] == pytest.approx(-0.05)
    assert result.p_value == pytest.approx(0.5)
