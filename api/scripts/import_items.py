"""Işıl'ın öğe tablosunu `content.items`'a aktarır.

    cd api
    uv run python -m scripts.import_items dosya.xlsx            # yalnızca rapor
    uv run python -m scripts.import_items dosya.xlsx --apply    # yazar

Öğe kimlikleri olaylara ve müfredatlara bağlı olduğu için korunur: satır silinmez, tablodan
çıkan öğe pasifleşir; Türkçe karşılığı düzeltilen öğe aynı kimlikle güncellenir. Gerçek havuz
yazılınca `dev-seed` öğeleri pasifleşir.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from lemminflect import getAllInflections
from sqlalchemy import Connection, text

from scripts.sheets import (
    Column,
    Report,
    Row,
    Spec,
    contains_term,
    owner_engine,
    read_sheet,
    turkish_fold,
    utf8_output,
)

DEFAULT_POOL = "v1"
DEV_POOL = "dev-seed"
KINDS = {"kelime": "word", "kalıp": "chunk", "yapı": "structure"}
LEVEL = re.compile(r"^(A1|A2)(?:\.([12]))?$")
TURKISH_LETTERS = re.compile(r"[çğışÇĞİŞ]")

SPEC = Spec(
    title="Öğe tablosu",
    file_name="oge-tablosu.xlsx",
    guide=(
        "Her satır bir öğe. Veri sayfasına yazın; başlıkları değiştirmeyin.",
        "Bir öğeyi kaldırmak için satırı silin: öğe pasifleşir, öğrenci geçmişi korunur.",
        "Örnek: go | kelime | A1.1 | gitmek | I go to work by bus. | Otobüsle işe giderim.",
    ),
    columns=(
        Column("en", "İngilizce", "Öğenin kendisi: go, every day, there is.", required=True),
        Column(
            "kind",
            "Tür",
            "kelime: tek kelime. kalıp: birlikte öğrenilen kelimeler. yapı: dilbilgisi yapısı.",
            required=True,
            choices=tuple(KINDS),
            width=12,
        ),
        Column(
            "level",
            "Seviye",
            "A1 ya da A2; biliniyorsa alt seviye (A1.1 önce öğretilir).",
            required=True,
            choices=("A1.1", "A1.2", "A1", "A2.1", "A2.2", "A2"),
            width=10,
        ),
        Column("tr", "Türkçe karşılık", "Öğrencinin göreceği karşılık.", required=True),
        Column("risk", "Hata riski notu", "Türkçe konuşanların tipik hatası.", width=34),
        Column("topics", "Konular", "Virgülle: iş, yemek, aile."),
        Column(
            "forms",
            "Çekimli biçimler",
            "Virgülle. Boşsa otomatik üretilir; düzensiz kalıplarda elle yazın.",
        ),
        Column("s1_en", "Örnek 1 (İngilizce)", "Öğenin geçtiği A1–A2 cümle.", width=34),
        Column("s1_tr", "Örnek 1 (Türkçe)", "Cümlenin çevirisi.", width=34),
        Column("s2_en", "Örnek 2 (İngilizce)", "İkinci cümle (isteğe bağlı).", width=34),
        Column("s2_tr", "Örnek 2 (Türkçe)", "Çevirisi.", width=34),
        Column("source", "Kaynak", "Öğenin geldiği liste (isteğe bağlı)."),
    ),
)


@dataclass(frozen=True, slots=True)
class ParsedItem:
    row: int
    kind: str
    text_en: str
    text_tr: str
    cefr: str
    sublevel: int | None
    forms: list[str]
    topics: list[str]
    error_risk_notes: str | None
    reference_sentences: list[dict[str, str]]
    source_list: str | None


def auto_forms(text_en: str, kind: str) -> list[str]:
    """Doğrulayıcının hedef öğeyi tanıması için çekimli biçimler."""
    if kind == "structure":
        return []
    words = text_en.lower().split()
    if len(words) == 1:
        table = getAllInflections(words[0])
    else:  # kalıpta yalnızca baştaki fiil çekilir: go to work -> goes to work
        table = getAllInflections(words[0], upos="VERB")
    rest = " ".join(words[1:])
    forms = {f"{form} {rest}".strip() for group in table.values() for form in group}
    return sorted(forms - {text_en.lower()})


def _commas(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _sentences(row: Row, kind: str, terms: list[str], report: Report) -> list[dict[str, str]]:
    sentences: list[dict[str, str]] = []
    for n in (1, 2):
        en, tr = row[f"s{n}_en"], row[f"s{n}_tr"]
        if bool(en) != bool(tr):
            report.error(row.number, f"örnek {n}: İngilizce ve Türkçe birlikte yazılmalı")
        elif en:
            if kind != "structure" and not contains_term(en, terms):
                report.error(row.number, f"örnek {n}: cümlede '{row['en']}' geçmiyor")
            sentences.append({"en": en, "tr": tr})
    return sentences


def parse_items(rows: list[Row], report: Report) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    seen: dict[tuple[str, str, str], int] = {}
    for row in rows:
        level = LEVEL.match(row["level"])
        if not (row["en"] and row["tr"] and row["kind"] in KINDS and level):
            continue  # alan hataları okurken raporlandı
        kind = KINDS[row["kind"]]
        if TURKISH_LETTERS.search(row["en"]):
            report.error(row.number, f"İngilizce sütununda Türkçe harf var: '{row['en']}'")
        if kind == "word" and " " in row["en"]:
            report.warn(row.number, f"'{row['en']}' kelime değil kalıp olabilir")

        key = (row["en"].casefold(), kind, turkish_fold(row["tr"]))
        if key in seen:
            report.error(row.number, f"'{row['en']}' satır {seen[key]} ile aynı")
            continue
        seen[key] = row.number

        forms = _commas(row["forms"]) or auto_forms(row["en"], kind)
        items.append(
            ParsedItem(
                row=row.number,
                kind=kind,
                text_en=row["en"],
                text_tr=row["tr"],
                cefr=level.group(1),
                sublevel=int(level.group(2)) if level.group(2) else None,
                forms=forms,
                topics=_commas(row["topics"]),
                error_risk_notes=row["risk"] or None,
                reference_sentences=_sentences(row, kind, [row["en"], *forms], report),
                source_list=row["source"] or None,
            )
        )
    without = sum(1 for i in items if not i.reference_sentences)
    if without:
        report.warn(None, f"{without} öğede örnek cümle yok (hatırlama testi bunlara dayanır)")
    return items


def apply_items(conn: Connection, items: list[ParsedItem], pool_version: str) -> dict[str, int]:
    """Yazar; commit çağırana aittir. Eşleşme: önce tam, sonra yalnızca İngilizce ve tür."""
    existing = conn.execute(
        text("SELECT id, kind, text_en, text_tr FROM content.items WHERE pool_version = :p"),
        {"p": pool_version},
    ).all()
    free = {row.id: row for row in existing}
    matches: dict[int, int] = {}  # tablo satırı -> öğe kimliği
    for item in items:
        for row in free.values():
            same_text = row.text_en.casefold() == item.text_en.casefold()
            same_meaning = turkish_fold(row.text_tr) == turkish_fold(item.text_tr)
            if same_text and same_meaning and row.kind == item.kind:
                matches[item.row] = row.id
                del free[row.id]
                break
    for item in items:
        if item.row in matches:
            continue
        for row in free.values():
            if row.text_en.casefold() == item.text_en.casefold() and row.kind == item.kind:
                matches[item.row] = row.id
                del free[row.id]
                break

    counts = {"yeni": 0, "güncellenen": 0, "pasifleşen": 0, "dev_pasifleşen": 0}
    for item in items:
        params = {
            "pool": pool_version,
            "kind": item.kind,
            "en": item.text_en,
            "tr": item.text_tr,
            "cefr": item.cefr,
            "sub": item.sublevel,
            "forms": item.forms,
            "topics": item.topics,
            "src": item.source_list,
            "risk": item.error_risk_notes,
            "refs": json.dumps(item.reference_sentences, ensure_ascii=False),
        }
        if item.row in matches:
            conn.execute(
                text(
                    "UPDATE content.items SET kind = :kind, text_en = :en, text_tr = :tr, "
                    "cefr = :cefr, sublevel = :sub, forms = :forms, topics = :topics, "
                    "source_list = :src, error_risk_notes = :risk, "
                    "reference_sentences = CAST(:refs AS jsonb), active = true WHERE id = :id"
                ),
                {**params, "id": matches[item.row]},
            )
            counts["güncellenen"] += 1
        else:
            conn.execute(
                text(
                    "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr, "
                    "sublevel, forms, topics, source_list, error_risk_notes, "
                    "reference_sentences) VALUES (:pool, :kind, :en, :tr, :cefr, :sub, :forms, "
                    ":topics, :src, :risk, CAST(:refs AS jsonb))"
                ),
                params,
            )
            counts["yeni"] += 1

    if free:
        result = conn.execute(
            text("UPDATE content.items SET active = false WHERE id = ANY(:ids) AND active"),
            {"ids": list(free)},
        )
        counts["pasifleşen"] = result.rowcount
    if pool_version != DEV_POOL:
        result = conn.execute(
            text("UPDATE content.items SET active = false WHERE pool_version = :d AND active"),
            {"d": DEV_POOL},
        )
        counts["dev_pasifleşen"] = result.rowcount
    return counts


def summary(items: list[ParsedItem]) -> str:
    by_level = {lvl: sum(1 for i in items if i.cefr == lvl) for lvl in ("A1", "A2")}
    by_kind = {k: sum(1 for i in items if i.kind == v) for k, v in KINDS.items()}
    return f"{len(items)} öğe: {by_level}, {by_kind}"


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Öğe tablosunu içe aktarır.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true", help="veritabanına yazar")
    parser.add_argument("--pool-version", default=DEFAULT_POOL)
    args = parser.parse_args()

    report = Report()
    items = parse_items(read_sheet(args.path, SPEC, report), report)
    report.print()
    if not report.ok:
        sys.exit(1)
    print(summary(items))

    engine = owner_engine()
    with engine.connect() as conn:
        counts = apply_items(conn, items, args.pool_version)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
    engine.dispose()
    print(f"{'Yazıldı' if args.apply else 'Deneme (yazılmadı; --apply ile yazılır)'}: {counts}")


if __name__ == "__main__":
    main()
