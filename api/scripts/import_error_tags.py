"""Hata etiketi tablosunu `content.error_tags`'a aktarır.

    cd api
    uv run python -m scripts.import_error_tags dosya.xlsx [--apply]

Etiketler `error_marks`'a bağlı olduğu için silinmez: tablodan çıkan etiket pasifleşir.
Ad ya da açıklama değişince `version` artar. Etiket listesi feedback prompt'unun statik
bloğuna girer; liste değişirse altın set yeniden koşulur.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Connection, text

from scripts.sheets import Column, Report, Row, Spec, owner_engine, read_sheet, utf8_output

CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
REQUIRED_CODE = "OTHER"  # doğrulayıcı katalog dışı hatalar için bu kodu bekler

SPEC = Spec(
    title="Hata etiketleri",
    file_name="hata-etiketleri.xlsx",
    guide=(
        "Öğrenci açıklamayı buradan okur; model yalnızca kodu seçer.",
        "OTHER satırı silinemez: katalog dışı hatalar için gereklidir.",
    ),
    columns=(
        Column("code", "Kod", "BÜYÜK_HARF, değiştirmeyin: ARTICLE, TENSE.", required=True),
        Column("name", "Türkçe ad", "Öğrencinin göreceği kısa ad.", required=True, width=30),
        Column("explanation", "Açıklama", "A1–A2 öğrencisine kısa kural.", required=True, width=60),
        Column("hint", "İpucu şablonu", "Doğru cevabı vermeyen ipucu.", width=40),
        Column(
            "l1",
            "Türkçeden kaynaklı",
            "Hata Türkçe alışkanlığından mı geliyor?",
            choices=("Evet", "Hayır"),
            width=12,
        ),
        Column("wrong", "Yanlış örnek", "I am go to work.", width=30),
        Column("right", "Doğru örnek", "I go to work.", width=30),
        Column("active", "Aktif", "Boşsa Evet.", choices=("Evet", "Hayır"), width=10),
    ),
)


@dataclass(frozen=True, slots=True)
class ParsedTag:
    code: str
    name_tr: str
    explanation_tr: str
    hint_template_tr: str | None
    l1_related: bool
    examples: list[dict[str, str]]
    active: bool


def parse_tags(rows: list[Row], report: Report) -> list[ParsedTag]:
    tags: list[ParsedTag] = []
    seen: dict[str, int] = {}
    for row in rows:
        code = row["code"]
        if not (code and row["name"] and row["explanation"]):
            continue
        if not CODE.match(code):
            report.error(row.number, f"kod '{code}' geçersiz (BÜYÜK_HARF ve _ olmalı)")
            continue
        if code in seen:
            report.error(row.number, f"kod '{code}' satır {seen[code]} ile aynı")
            continue
        seen[code] = row.number
        if bool(row["wrong"]) != bool(row["right"]):
            report.error(row.number, "yanlış ve doğru örnek birlikte yazılmalı")
        elif row["wrong"] and row["wrong"] == row["right"]:
            report.error(row.number, "yanlış ve doğru örnek aynı")
        examples = [{"wrong": row["wrong"], "right": row["right"]}] if row["wrong"] else []
        tags.append(
            ParsedTag(
                code=code,
                name_tr=row["name"],
                explanation_tr=row["explanation"],
                hint_template_tr=row["hint"] or None,
                l1_related=row["l1"] == "Evet",
                examples=examples,
                active=row["active"] != "Hayır",
            )
        )
    if not any(t.code == REQUIRED_CODE and t.active for t in tags):
        report.error(None, f"{REQUIRED_CODE} etiketi aktif olarak bulunmalı")
    return tags


def apply_tags(conn: Connection, tags: list[ParsedTag]) -> dict[str, int]:
    """Yazar; commit çağırana aittir."""
    existing = {
        row.code: row
        for row in conn.execute(
            text("SELECT code, name_tr, explanation_tr, version FROM content.error_tags")
        )
    }
    counts = {"yeni": 0, "güncellenen": 0, "pasifleşen": 0}
    for tag in tags:
        old = existing.pop(tag.code, None)
        changed = old is not None and (
            (old.name_tr, old.explanation_tr) != (tag.name_tr, tag.explanation_tr)
        )
        version = 1 if old is None else old.version + int(changed)
        conn.execute(
            text(
                "INSERT INTO content.error_tags (code, name_tr, explanation_tr, "
                "hint_template_tr, l1_related, examples, version, active) "
                "VALUES (:c, :n, :e, :h, :l, CAST(:x AS jsonb), :v, :a) "
                "ON CONFLICT (code) DO UPDATE SET name_tr = :n, explanation_tr = :e, "
                "hint_template_tr = :h, l1_related = :l, examples = CAST(:x AS jsonb), "
                "version = :v, active = :a"
            ),
            {
                "c": tag.code,
                "n": tag.name_tr,
                "e": tag.explanation_tr,
                "h": tag.hint_template_tr,
                "l": tag.l1_related,
                "x": json.dumps(tag.examples, ensure_ascii=False),
                "v": version,
                "a": tag.active,
            },
        )
        counts["yeni" if old is None else "güncellenen"] += 1
    if existing:
        result = conn.execute(
            text("UPDATE content.error_tags SET active = false WHERE code = ANY(:c) AND active"),
            {"c": list(existing)},
        )
        counts["pasifleşen"] = result.rowcount
    return counts


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Hata etiketlerini içe aktarır.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true", help="veritabanına yazar")
    args = parser.parse_args()

    report = Report()
    tags = parse_tags(read_sheet(args.path, SPEC, report), report)
    report.print()
    if not report.ok:
        sys.exit(1)

    engine = owner_engine()
    with engine.connect() as conn:
        counts = apply_tags(conn, tags)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
    engine.dispose()
    print(f"{'Yazıldı' if args.apply else 'Deneme (yazılmadı; --apply ile yazılır)'}: {counts}")


if __name__ == "__main__":
    main()
