"""Seviye testi inceleme listesini içe aktarır: Onay / Değiştir / Çıkar.

    cd api
    uv run python -m scripts.import_placement dosya.xlsx
    uv run python -m scripts.import_placement dosya.xlsx --form B
    uv run python -m scripts.import_placement dosya.xlsx --apply --reviewer "Işıl"

Hepsi Onay ise mevcut sürüm onaylanır. Değişiklik varsa yeni sürüm açılır; eski sürüm
dokunulmadan kalır, çünkü verilmiş cevaplar ona bağlıdır.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import Connection, text

from app.onboarding.placement import FixedQuestion
from scripts.sheets import Column, Report, Row, Spec, owner_engine, read_sheet, utf8_output

SECTIONS = {
    "kelime": "vocabulary",
    "dilbilgisi": "grammar",
    "okuma": "reading",
    "dinleme": "listening",
}
SECTION_LABELS = {v: k for k, v in SECTIONS.items()}
APPROVE, CHANGE, REMOVE = "Onay", "Değiştir", "Çıkar"
OPTION_KEYS = ("o1", "o2", "o3", "o4")
MAX_LEVEL_GAP = 2  # puanlama seviye başına oran kullanır; çok dengesiz test güvenilmez olur

SPEC = Spec(
    title="Yerleştirme testi incelemesi",
    file_name="yerlestirme-inceleme.xlsx",
    guide=(
        "Her satır için Karar seçin: Onay, Değiştir ya da Çıkar. Boş karar kabul edilmez.",
        "Değiştir: aynı satırda soruyu düzeltin ve Karar'ı Değiştir yapın.",
        "Yeni soru: en alta satır ekleyin, Kimlik boş kalsın, Karar Değiştir olsun.",
        "Doğru cevap şıklardan biriyle harfi harfine aynı olmalı.",
    ),
    columns=(
        Column("id", "Kimlik", "Değiştirmeyin. Yeni soruda boş bırakın.", width=9),
        Column(
            "section",
            "Bölüm",
            "Sorunun ölçtüğü beceri.",
            required=True,
            choices=tuple(SECTIONS),
            width=12,
        ),
        Column("level", "Seviye", "A1 ya da A2.", required=True, choices=("A1", "A2"), width=9),
        Column("passage", "Okuma metni", "Yalnızca okuma sorularında.", width=40),
        Column("prompt", "Soru", "Öğrencinin göreceği soru.", required=True, width=44),
        Column("o1", "Şık 1", "Zorunlu.", required=True, width=18),
        Column("o2", "Şık 2", "Zorunlu.", required=True, width=18),
        Column("o3", "Şık 3", "İsteğe bağlı.", width=18),
        Column("o4", "Şık 4", "İsteğe bağlı.", width=18),
        Column("answer", "Doğru cevap", "Şıklardan biri.", required=True, width=18),
        Column(
            "decision",
            "Karar",
            "Onay, Değiştir ya da Çıkar.",
            required=True,
            choices=(APPROVE, CHANGE, REMOVE),
            width=11,
        ),
        Column("note", "Not", "Emir'e not (içe aktarılmaz).", width=34),
    ),
)


SPEC_B = replace(
    SPEC, title="Seviye testi B formu incelemesi", file_name="yerlestirme-inceleme-b.xlsx"
)


@dataclass(frozen=True, slots=True)
class PlacementPlan:
    questions: list[FixedQuestion]
    changed: bool
    removed: int


def question_row(question: FixedQuestion) -> dict[str, str]:
    """Şablonun önceden doldurulmuş satırı; karar boş kalır."""
    values = {
        "id": question.id,
        "section": SECTION_LABELS[question.section],
        "level": question.level,
        "passage": question.passage or "",
        "prompt": question.prompt,
        "answer": question.answer,
    }
    values.update(zip(OPTION_KEYS, question.options, strict=False))
    return values


def _question(row: Row, report: Report) -> FixedQuestion | None:
    options = [row[k] for k in OPTION_KEYS if row[k]]
    if len(set(options)) != len(options):
        report.error(row.number, "şıklar birbirinin aynı")
        return None
    if row["answer"] not in options:
        report.error(row.number, f"doğru cevap '{row['answer']}' şıklarda yok")
        return None
    if row["section"] == "okuma" and not row["passage"]:
        report.error(row.number, "okuma sorusunda metin boş")
        return None
    identity = row["id"] or "n" + hashlib.sha256(row["prompt"].encode()).hexdigest()[:8]
    try:
        return FixedQuestion(
            id=identity,
            section=SECTIONS[row["section"]],  # type: ignore[arg-type]
            level=row["level"],  # type: ignore[arg-type]
            prompt=row["prompt"],
            options=options,
            answer=row["answer"],
            passage=row["passage"] or None,
        )
    except ValidationError as exc:
        report.error(row.number, f"soru geçersiz: {exc.errors()[0]['msg']}")
        return None


def plan_placement(rows: list[Row], base: list[FixedQuestion], report: Report) -> PlacementPlan:
    """Tablo ile mevcut sürümü karşılaştırır; sessizce soru kaybolmasına izin vermez."""
    originals = {q.id: q for q in base}
    seen: dict[str, int] = {}
    questions: list[FixedQuestion] = []
    changed = False
    removed = 0
    for row in rows:
        if row["id"]:
            if row["id"] in seen:
                report.error(row.number, f"kimlik '{row['id']}' satır {seen[row['id']]} ile aynı")
                continue
            seen[row["id"]] = row.number
            if row["id"] not in originals:
                report.error(row.number, f"kimlik '{row['id']}' mevcut sürümde yok")
                continue
        if row["section"] not in SECTIONS or row["decision"] not in (APPROVE, CHANGE, REMOVE):
            continue  # alan hataları okurken raporlandı
        if not row["id"] and row["decision"] != CHANGE:
            report.error(row.number, "kimliksiz yeni soruda Karar Değiştir olmalı")
            continue

        if row["decision"] == REMOVE:
            removed += 1
            changed = True
            continue
        question = _question(row, report)
        if question is None:
            continue
        original = originals.get(question.id)
        if row["decision"] == APPROVE and question != original:
            report.error(row.number, "içerik değişmiş ama Karar Onay; Değiştir olmalı")
        if row["decision"] == CHANGE:
            if question == original:
                report.warn(row.number, "Karar Değiştir ama içerik aynı")
            else:
                changed = True
        questions.append(question)

    for missing in originals.keys() - seen.keys():
        report.error(None, f"'{missing}' sorusu tabloda yok; kaldırmak için Karar Çıkar seçin")
    levels = [sum(1 for q in questions if q.level == lvl) for lvl in ("A1", "A2")]
    if abs(levels[0] - levels[1]) > MAX_LEVEL_GAP:
        report.warn(None, f"seviyeler dengesiz: A1 {levels[0]}, A2 {levels[1]}")
    return PlacementPlan(questions, changed, removed)


def latest_version(conn: Connection, form: str = "A") -> tuple[int, list[FixedQuestion]] | None:
    row = conn.execute(
        text(
            "SELECT version, questions FROM content.fixed_tests "
            "WHERE purpose = 'placement' AND form = :f ORDER BY version DESC LIMIT 1"
        ),
        {"f": form},
    ).first()
    if row is None:
        return None
    return row.version, [FixedQuestion.model_validate(q) for q in row.questions]


def apply_placement(
    conn: Connection, plan: PlacementPlan, version: int, reviewer: str, form: str = "A"
) -> int:
    """Onaylı sürümü döndürür; commit çağırana aittir."""
    if not plan.changed:
        conn.execute(
            text(
                "UPDATE content.fixed_tests SET approved_by = :r, approved_at = now() "
                "WHERE purpose = 'placement' AND form = :f AND version = :v"
            ),
            {"r": reviewer, "f": form, "v": version},
        )
        return version
    conn.execute(
        text(
            "INSERT INTO content.fixed_tests (purpose, form, version, questions, approved_by, "
            "approved_at) VALUES ('placement', :f, :v, CAST(:q AS jsonb), :r, now())"
        ),
        {
            "f": form,
            "v": version + 1,
            "q": json.dumps([q.model_dump() for q in plan.questions], ensure_ascii=False),
            "r": reviewer,
        },
    )
    return version + 1


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Yerleştirme incelemesini içe aktarır.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--form", choices=("A", "B"), default="A", help="hangi form")
    parser.add_argument("--apply", action="store_true", help="veritabanına yazar")
    parser.add_argument("--reviewer", help="onaylayan kişi (--apply ile zorunlu)")
    args = parser.parse_args()
    if args.apply and not args.reviewer:
        parser.error("--apply için --reviewer gerekir")

    engine = owner_engine()
    with engine.connect() as conn:
        base = latest_version(conn, args.form)
        if base is None:
            sys.exit("Yerleştirme testi yok; önce: uv run python -m scripts.seed_dev_content")
        version, questions = base
        report = Report()
        spec = SPEC_B if args.form == "B" else SPEC
        plan = plan_placement(read_sheet(args.path, spec, report), questions, report)
        report.print()
        if not report.ok:
            sys.exit(1)
        print(f"{len(plan.questions)} soru, {plan.removed} çıkarıldı, değişiklik: {plan.changed}")
        if not args.apply:
            target = version + 1 if plan.changed else version
            print(f"Deneme (yazılmadı): sürüm {target} onaylanacak.")
            return
        approved = apply_placement(conn, plan, version, args.reviewer, args.form)
        conn.commit()
    engine.dispose()
    print(f"Yazıldı: sürüm {approved} onaylandı.")


if __name__ == "__main__":
    main()
