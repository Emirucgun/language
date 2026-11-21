"""Işıl'ın tabloları: şablon, satır bazlı rapor, içe aktarma."""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text

from app.onboarding.placement import FixedQuestion
from scripts import make_templates
from scripts.import_error_tags import SPEC as TAG_SPEC
from scripts.import_error_tags import apply_tags, parse_tags
from scripts.import_golden import SPEC as GOLDEN_SPEC
from scripts.import_golden import auto_split, parse_golden, read_previous, write_cases
from scripts.import_items import SPEC as ITEM_SPEC
from scripts.import_items import apply_items, auto_forms, parse_items
from scripts.import_placement import SPEC as PLACEMENT_SPEC
from scripts.import_placement import (
    apply_placement,
    latest_version,
    plan_placement,
    question_row,
)
from scripts.placement_v1 import QUESTIONS
from scripts.sheets import Report, Row, Spec, read_sheet, write_template
from tests.conftest import migrated_db  # noqa: F401

CODES = {"ARTICLE", "TENSE", "OTHER"}


def _rows(tmp_path: Path, spec: Spec, rows: list[dict[str, str]], report: Report) -> list[Row]:
    """Gerçek dosya üzerinden gider: şablon ve okuma aynı sütun tanımını kullanmalı."""
    path = tmp_path / spec.file_name
    write_template(path, spec, rows)
    return read_sheet(path, spec, report)


def _item(**values: str) -> dict[str, str]:
    return {"en": "go", "kind": "kelime", "level": "A1.1", "tr": "gitmek", **values}


# --- Ortak okuma ve rapor ---


def test_empty_required_cell_is_reported_with_the_sheet_row(tmp_path: Path) -> None:
    report = Report()
    _rows(tmp_path, ITEM_SPEC, [_item(), _item(en="live", tr="yaşamak", level="")], report)
    assert report.errors == ["satır 3: Seviye boş"]


def test_choices_are_case_insensitive_and_invalid_ones_are_reported(tmp_path: Path) -> None:
    report = Report()
    rows = _rows(tmp_path, ITEM_SPEC, [_item(kind="KELİME"), _item(kind="fiil", tr="x")], report)
    assert len(report.errors) == 1  # KELİME kabul edildi
    assert "satır 3: Tür 'fiil' geçersiz" in report.errors[0]
    assert rows[0]["kind"] == "kelime"


def test_missing_column_and_sheet_are_reported(tmp_path: Path) -> None:
    path = tmp_path / "x.xlsx"
    write_template(path, GOLDEN_SPEC)
    report = Report()
    assert read_sheet(path, ITEM_SPEC, report) == []
    assert "eksik sütun" in report.errors[0]


def test_blank_rows_are_skipped_and_numbers_stay_true(tmp_path: Path) -> None:
    report = Report()
    rows = _rows(tmp_path, ITEM_SPEC, [_item(), {}, _item(en="live", tr="yaşamak")], report)
    assert [r.number for r in rows] == [2, 4]


# --- Öğeler ---


def test_forms_are_generated_for_words_and_leading_verbs() -> None:
    assert {"went", "goes", "going"} <= set(auto_forms("go", "word"))
    assert "goes to work" in auto_forms("go to work", "chunk")
    assert auto_forms("every day", "chunk") == []
    assert auto_forms("present simple", "structure") == []


def test_item_fields_are_parsed(tmp_path: Path) -> None:
    report = Report()
    row = _item(
        s1_en="She goes to work.",
        s1_tr="O işe gider.",
        topics="iş, günlük",
        risk="-s unutulur",
        forms="goes, went",
    )
    [item] = parse_items(_rows(tmp_path, ITEM_SPEC, [row], report), report)
    assert report.ok
    assert (item.kind, item.cefr, item.sublevel) == ("word", "A1", 1)
    assert item.forms == ["goes", "went"]
    assert item.topics == ["iş", "günlük"]
    assert item.reference_sentences == [{"en": "She goes to work.", "tr": "O işe gider."}]


def test_item_without_base_form_in_examples_is_warned(tmp_path: Path) -> None:
    """Hatırlama testi boşluğa yalın hâli koyar; "She goes" ile öğe teste giremez."""
    report = Report()
    inflected = _item(s1_en="She goes to work.", s1_tr="O işe gider.", forms="goes")
    parse_items(_rows(tmp_path, ITEM_SPEC, [inflected], report), report)
    assert report.ok and any("yalın" in w for w in map(str, report.warnings))

    report = Report()
    plain = _item(s1_en="I go to work.", s1_tr="İşe giderim.", forms="goes")
    parse_items(_rows(tmp_path, ITEM_SPEC, [plain], report), report)
    assert not any("yalın" in w for w in map(str, report.warnings))


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (_item(en="gitmek"), None),
        (_item(en="kitaplık"), "Türkçe harf"),
        (_item(s1_en="I eat.", s1_tr="Yerim."), "geçmiyor"),
        (_item(s1_en="I go."), "birlikte"),
    ],
)
def test_item_content_checks(tmp_path: Path, row: dict[str, str], message: str | None) -> None:
    report = Report()
    parse_items(_rows(tmp_path, ITEM_SPEC, [row], report), report)
    if message is None:
        assert report.ok
    else:
        assert message in report.errors[0]
        assert report.errors[0].startswith("satır 2:")


def test_duplicates_are_errors_but_a_second_meaning_is_allowed(tmp_path: Path) -> None:
    report = Report()
    rows = [
        _item(en="light", tr="ışık"),
        _item(en="light", tr="hafif"),
        _item(en="Light", tr="Işık"),
    ]
    parse_items(_rows(tmp_path, ITEM_SPEC, rows, report), report)
    assert len(report.errors) == 1
    assert report.errors[0].startswith("satır 4:")


def test_missing_sentences_are_one_summary_warning(tmp_path: Path) -> None:
    report = Report()
    rows = [_item(), _item(en="live", tr="yaşamak")]
    parse_items(_rows(tmp_path, ITEM_SPEC, rows, report), report)
    assert report.ok
    assert report.warnings == ["2 öğede örnek cümle yok (hatırlama testi bunlara dayanır)"]


@pytest.fixture
def conn(migrated_db: Config) -> Iterator[Connection]:
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with engine.connect() as connection:
        yield connection
        connection.rollback()
    engine.dispose()


def _parsed(tmp_path: Path, rows: list[dict[str, str]]) -> list:  # type: ignore[type-arg]
    report = Report()
    items = parse_items(_rows(tmp_path, ITEM_SPEC, rows, report), report)
    assert report.ok
    return items


def _pool(conn: Connection) -> dict[str, tuple[int, str, bool]]:
    rows = conn.execute(
        text("SELECT id, text_en, text_tr, active FROM content.items WHERE pool_version = 't'")
    )
    return {r.text_en: (r.id, r.text_tr, r.active) for r in rows}


def test_reimport_keeps_ids_and_deactivates_instead_of_deleting(
    tmp_path: Path, conn: Connection
) -> None:
    first = _parsed(tmp_path, [_item(), _item(en="live", tr="yaşamak")])
    assert apply_items(conn, first, "t")["yeni"] == 2
    before = _pool(conn)

    # "go" çevirisi düzeltildi, "live" tablodan çıktı, "eat" eklendi.
    second = _parsed(tmp_path, [_item(tr="gitmek, varmak"), _item(en="eat", tr="yemek")])
    counts = apply_items(conn, second, "t")
    after = _pool(conn)

    assert (counts["yeni"], counts["güncellenen"], counts["pasifleşen"]) == (1, 1, 1)
    assert after["go"] == (before["go"][0], "gitmek, varmak", True)
    assert after["live"] == (before["live"][0], "yaşamak", False)
    assert after["eat"][2] is True


def test_second_meaning_keeps_its_own_id(tmp_path: Path, conn: Connection) -> None:
    rows = [_item(en="light", tr="ışık"), _item(en="light", tr="hafif")]
    apply_items(conn, _parsed(tmp_path, rows), "t")
    ids = {
        r.text_tr: r.id
        for r in conn.execute(
            text("SELECT id, text_tr FROM content.items WHERE pool_version = 't'")
        )
    }
    apply_items(conn, _parsed(tmp_path, list(reversed(rows))), "t")
    again = {
        r.text_tr: r.id
        for r in conn.execute(
            text("SELECT id, text_tr FROM content.items WHERE pool_version = 't'")
        )
    }
    assert ids == again


def test_real_pool_deactivates_dev_seed(tmp_path: Path, conn: Connection) -> None:
    conn.execute(
        text(
            "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr) "
            "VALUES ('dev-seed', 'word', 'seed', 'tohum', 'A1')"
        )
    )
    apply_items(conn, _parsed(tmp_path, [_item()]), "t")
    active = conn.scalar(
        text("SELECT bool_or(active) FROM content.items WHERE pool_version = 'dev-seed'")
    )
    assert active is False


# --- Hata etiketleri ---


def _tag(**values: str) -> dict[str, str]:
    return {"code": "OTHER", "name": "Diğer", "explanation": "Katalog dışı.", **values}


def test_other_tag_is_required(tmp_path: Path) -> None:
    report = Report()
    rows = [_tag(code="ARTICLE"), _tag(code="tense"), _tag(code="ARTICLE")]
    parse_tags(_rows(tmp_path, TAG_SPEC, rows, report), report)
    assert any("satır 3" in e and "geçersiz" in e for e in report.errors)
    assert any("satır 4" in e and "aynı" in e for e in report.errors)
    assert any("OTHER" in e for e in report.errors)


def test_tag_version_grows_only_when_text_changes(tmp_path: Path, conn: Connection) -> None:
    def load(**values: str) -> None:
        report = Report()
        tags = parse_tags(_rows(tmp_path, TAG_SPEC, [_tag(**values)], report), report)
        assert report.ok
        apply_tags(conn, tags)

    def version() -> int:
        return conn.scalar(text("SELECT version FROM content.error_tags WHERE code = 'OTHER'"))

    load()
    start = version()
    load(hint="ipucu")
    assert version() == start
    load(explanation="Yeni açıklama.")
    assert version() == start + 1


# --- Yerleştirme incelemesi ---

BANK = [FixedQuestion.model_validate(q) for q in QUESTIONS]


def _review(**decisions: str) -> list[dict[str, str]]:
    return [{**question_row(q), "decision": decisions.get(q.id, "Onay")} for q in BANK]


def _plan(tmp_path: Path, rows: list[dict[str, str]]) -> tuple[Report, object]:
    report = Report()
    plan = plan_placement(_rows(tmp_path, PLACEMENT_SPEC, rows, report), BANK, report)
    return report, plan


def test_all_approved_changes_nothing(tmp_path: Path) -> None:
    report, plan = _plan(tmp_path, _review())
    assert report.ok, report.errors
    assert plan.changed is False  # type: ignore[attr-defined]
    assert plan.questions == BANK  # type: ignore[attr-defined]


def test_empty_decision_is_an_error(tmp_path: Path) -> None:
    rows = _review()
    rows[0]["decision"] = ""
    report, _ = _plan(tmp_path, rows)
    assert report.errors == ["satır 2: Karar boş"]  # ayrıca "tabloda yok" denmez


def test_edit_without_change_decision_is_caught(tmp_path: Path) -> None:
    rows = _review()
    rows[0]["prompt"] = "Değişti"
    report, _ = _plan(tmp_path, rows)
    assert any("Karar Onay" in e for e in report.errors)


def test_removed_row_must_be_explicit(tmp_path: Path) -> None:
    report, _ = _plan(tmp_path, _review()[1:])
    assert any(BANK[0].id in e and "Çıkar" in e for e in report.errors)

    report, plan = _plan(tmp_path, _review(**{BANK[0].id: "Çıkar"}))
    assert report.ok
    assert (plan.changed, plan.removed) == (True, 1)  # type: ignore[attr-defined]


def test_answer_must_be_an_option_and_new_rows_get_an_id(tmp_path: Path) -> None:
    rows = _review()
    rows[0].update(answer="yok", decision="Değiştir")
    report, _ = _plan(tmp_path, rows)
    assert any("şıklarda yok" in e for e in report.errors)

    extra = {
        "section": "kelime",
        "level": "A2",
        "prompt": "Yeni soru",
        "o1": "a",
        "o2": "b",
        "answer": "a",
        "decision": "Değiştir",
    }
    report, plan = _plan(tmp_path, [*_review(), extra])
    assert report.ok
    assert plan.changed is True  # type: ignore[attr-defined]
    assert plan.questions[-1].id.startswith("n")  # type: ignore[attr-defined]


def test_approval_updates_or_adds_a_version(tmp_path: Path, conn: Connection) -> None:
    conn.execute(text("DELETE FROM content.fixed_tests WHERE purpose = 'placement'"))
    conn.execute(
        text(
            "INSERT INTO content.fixed_tests (purpose, version, questions) "
            "VALUES ('placement', 1, CAST(:q AS jsonb))"
        ),
        {"q": json.dumps([q.model_dump() for q in BANK], ensure_ascii=False)},
    )
    _, same = _plan(tmp_path, _review())
    assert apply_placement(conn, same, 1, "Işıl") == 1  # type: ignore[arg-type]

    _, edited = _plan(tmp_path, _review(**{BANK[0].id: "Çıkar"}))
    assert apply_placement(conn, edited, 1, "Işıl") == 2  # type: ignore[arg-type]

    rows = conn.execute(
        text(
            "SELECT version, jsonb_array_length(questions) AS n, approved_by "
            "FROM content.fixed_tests WHERE purpose = 'placement' ORDER BY version"
        )
    ).all()
    assert [tuple(r) for r in rows] == [(1, 24, "Işıl"), (2, 23, "Işıl")]


def test_forms_are_versioned_separately(tmp_path: Path, conn: Connection) -> None:
    conn.execute(text("DELETE FROM content.fixed_tests WHERE purpose = 'placement'"))
    for form in ("A", "B"):
        conn.execute(
            text(
                "INSERT INTO content.fixed_tests (purpose, form, version, questions) "
                "VALUES ('placement', :f, 1, CAST(:q AS jsonb))"
            ),
            {"f": form, "q": json.dumps([q.model_dump() for q in BANK], ensure_ascii=False)},
        )
    _, edited = _plan(tmp_path, _review(**{BANK[0].id: "Çıkar"}))
    assert apply_placement(conn, edited, 1, "Işıl", "B") == 2  # type: ignore[arg-type]

    latest = latest_version(conn, "A")
    assert latest is not None and latest[0] == 1
    latest = latest_version(conn, "B")
    assert latest is not None and latest[0] == 2 and len(latest[1]) == 23
    conn.execute(text("DELETE FROM content.fixed_tests WHERE form = 'B'"))


# --- Altın set ---


def _case(**values: str) -> dict[str, str]:
    return {
        "text": "I am go to work.",
        "has_error": "Evet",
        "tags": "TENSE",
        "corrections": "I go to work. | I am going to work.",
        **values,
    }


def _golden(tmp_path: Path, rows: list[dict[str, str]], report: Report) -> list:  # type: ignore[type-arg]
    return parse_golden(_rows(tmp_path, GOLDEN_SPEC, rows, report), CODES, report)


def test_golden_row_is_parsed(tmp_path: Path) -> None:
    report = Report()
    [case] = _golden(tmp_path, [_case(split="test", kind="enjeksiyon")], report)
    assert report.ok
    assert case.corrections == ["I go to work.", "I am going to work."]
    assert (case.has_error, case.split, case.kind) == (True, "test", "enjeksiyon")


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (_case(tags=""), "etiket boş"),
        (_case(corrections=""), "düzeltme boş"),
        (_case(tags="ARTİCLE"), "katalogda yok"),
        (_case(has_error="Hayır"), "hata yok ama"),
        (_case(corrections="i am  GO to work."), "aynısı"),
    ],
)
def test_golden_label_checks(tmp_path: Path, row: dict[str, str], message: str) -> None:
    report = Report()
    _golden(tmp_path, [row], report)
    assert any(message in e and e.startswith("satır 2:") for e in report.errors)


def test_same_sentence_cannot_appear_twice(tmp_path: Path) -> None:
    report = Report()
    _golden(tmp_path, [_case(split="dev"), _case(text="i am go  to WORK.", split="test")], report)
    assert report.errors == ["satır 3: cümle satır 2 ile aynı"]


def test_auto_split_is_stable_and_near_thirty_percent() -> None:
    sentences = [f"Sentence number {i}." for i in range(1000)]
    splits = [auto_split(s) for s in sentences]
    assert splits == [auto_split(s) for s in sentences]
    assert 0.25 < splits.count("dev") / 1000 < 0.35


def test_test_sentence_cannot_move_to_dev(tmp_path: Path) -> None:
    report = Report()
    [case] = _golden(tmp_path, [_case(split="test")], report)
    path = tmp_path / "golden.jsonl"
    write_cases(path, [case])
    assert read_previous(path) == {case.id: "test"}

    rows = _rows(tmp_path, GOLDEN_SPEC, [_case(split="dev")], report)
    parse_golden(rows, CODES, report, read_previous(path))
    assert any("dev'e alınamaz" in e for e in report.errors)


# --- Üretilen şablonlar ---


@pytest.mark.parametrize("spec", [ITEM_SPEC, GOLDEN_SPEC, TAG_SPEC, PLACEMENT_SPEC])
def test_committed_templates_match_the_columns(spec: Spec) -> None:
    report = Report()
    read_sheet(make_templates.OUTPUT / spec.file_name, spec, report)
    assert not any("eksik sütun" in e for e in report.errors)


def test_generated_templates_can_be_read_back(tmp_path: Path) -> None:
    make_templates.main(tmp_path)
    for spec in (ITEM_SPEC, GOLDEN_SPEC):
        report = Report()
        assert read_sheet(tmp_path / spec.file_name, spec, report) == []
        assert report.ok

    report = Report()
    tags = parse_tags(read_sheet(tmp_path / TAG_SPEC.file_name, TAG_SPEC, report), report)
    assert report.ok
    assert len(tags) == 8

    # Yerleştirme şablonunda karar bilerek boş: Işıl seçene kadar içe aktarılmaz.
    report = Report()
    rows = read_sheet(tmp_path / PLACEMENT_SPEC.file_name, PLACEMENT_SPEC, report)
    assert len(rows) == len(BANK)
    assert len(report.errors) == len(BANK)
