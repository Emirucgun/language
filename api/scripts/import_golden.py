"""Işıl'ın altın set tablosunu `eval/golden/feedback.jsonl` dosyasına aktarır.

    cd api
    uv run python -m scripts.import_golden dosya.xlsx [--apply]

Altın set veritabanına değil depoya girer: prompt ve model ölçümleri sürümlü olur.
Bölme boşsa cümleden kararlı olarak üretilir (yaklaşık %30 dev). `test` bölmesindeki bir
cümle `dev`e alınamaz: prompt ayarında görülen cümle ölçümü geçersiz kılar.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import text

from scripts.sheets import (
    Column,
    Report,
    Row,
    Spec,
    owner_engine,
    read_sheet,
    split_multi,
    utf8_output,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "eval/golden/feedback.jsonl"
YES, NO = "Evet", "Hayır"
DEV, TEST = "dev", "test"
DEV_PERCENT = 30
DEV_SHARE_RANGE = (0.2, 0.4)
MIN_ROWS_FOR_SHARE_CHECK = 20

SPEC = Spec(
    title="Altın set",
    file_name="altin-set.xlsx",
    guide=(
        "Her satır bir öğrenci cümlesi. Gerçek kişi adı ve kişisel bilgi yazmayın.",
        "Birden fazla etiket ya da düzeltme varsa aralarına | koyun.",
        "Bölme boşsa otomatik atanır. test bölmesi prompt ayarında hiç kullanılmaz.",
        "Enjeksiyon satırları modeli kandırmaya çalışan cümlelerdir (önceki talimatları unut).",
    ),
    columns=(
        Column("text", "Cümle", "Öğrencinin yazdığı metin, olduğu gibi.", required=True, width=44),
        Column(
            "has_error",
            "Hata var mı",
            "Cümlede düzeltilmesi gereken hata var mı?",
            required=True,
            choices=(YES, NO),
            width=10,
        ),
        Column("tags", "Etiketler", "Hata kodları: ARTICLE | TENSE.", width=24),
        Column(
            "corrections",
            "Kabul edilen düzeltmeler",
            "Kabul edilen doğru cümleler; | ile ayırın.",
            width=50,
        ),
        Column("split", "Bölme", "dev ya da test; boşsa otomatik.", choices=(DEV, TEST), width=9),
        Column("task", "Görev", "Öğrenciye verilen görev (isteğe bağlı).", width=34),
        Column("target", "Hedef öğe", "Çalışılan öğe (isteğe bağlı): go.", width=18),
        Column("kind", "Tür", "Boşsa normal.", choices=("normal", "enjeksiyon"), width=12),
        Column("note", "Not", "Kendi notunuz.", width=30),
    ),
)


@dataclass(frozen=True, slots=True)
class GoldenCase:
    id: str
    text: str
    has_error: bool
    tags: list[str]
    corrections: list[str]
    split: str
    task: str | None
    target: str | None
    kind: str
    note: str | None


def _normalized(sentence: str) -> str:
    return " ".join(sentence.casefold().split())


def _digest(sentence: str) -> str:
    return hashlib.sha256(_normalized(sentence).encode()).hexdigest()


def auto_split(sentence: str) -> str:
    return DEV if int(_digest(sentence)[:8], 16) % 100 < DEV_PERCENT else TEST


def _check_labels(row: Row, tags: list[str], fixes: list[str], report: Report) -> None:
    if row["has_error"] == YES:
        if not tags:
            report.error(row.number, "hata var ama etiket boş")
        if not fixes:
            report.error(row.number, "hata var ama kabul edilen düzeltme boş")
    elif row["has_error"] == NO and (tags or fixes):
        report.error(row.number, "hata yok ama etiket ya da düzeltme yazılmış")
    if any(_normalized(fix) == _normalized(row["text"]) for fix in fixes):
        report.error(row.number, "düzeltme cümlenin aynısı")


def parse_golden(
    rows: list[Row],
    codes: set[str],
    report: Report,
    previous: dict[str, str] | None = None,
) -> list[GoldenCase]:
    """`previous`: daha önce aktarılmış kimlik → bölme."""
    cases: list[GoldenCase] = []
    seen: dict[str, int] = {}
    for row in rows:
        if not (row["text"] and row["has_error"] in (YES, NO)):
            continue
        key = _normalized(row["text"])
        if key in seen:  # aynı cümle iki bölmede olursa ölçüm sızar
            report.error(row.number, f"cümle satır {seen[key]} ile aynı")
            continue
        seen[key] = row.number

        tags = list(dict.fromkeys(split_multi(row["tags"])))
        for tag in tags:
            if tag not in codes:
                report.error(row.number, f"etiket '{tag}' katalogda yok")
        fixes = split_multi(row["corrections"])
        _check_labels(row, tags, fixes, report)

        identity = "g" + _digest(row["text"])[:10]
        split = row["split"] or auto_split(row["text"])
        if (previous or {}).get(identity) == TEST and split == DEV:
            report.error(row.number, "cümle test bölmesindeydi; dev'e alınamaz")
        cases.append(
            GoldenCase(
                id=identity,
                text=row["text"],
                has_error=row["has_error"] == YES,
                tags=tags,
                corrections=fixes,
                split=split,
                task=row["task"] or None,
                target=row["target"] or None,
                kind=row["kind"] or "normal",
                note=row["note"] or None,
            )
        )
    if len(cases) >= MIN_ROWS_FOR_SHARE_CHECK:
        share = sum(1 for c in cases if c.split == DEV) / len(cases)
        low, high = DEV_SHARE_RANGE
        if not low <= share <= high:
            report.warn(None, f"dev oranı %{share * 100:.0f}; hedef yaklaşık %{DEV_PERCENT}")
    return cases


def read_previous(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    return {case["id"]: case["split"] for case in cases}


def write_cases(path: Path, cases: list[GoldenCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(case), ensure_ascii=False) for case in cases]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Altın seti içe aktarır.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--apply", action="store_true", help="JSONL dosyasını yazar")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    engine = owner_engine()
    with engine.connect() as conn:
        codes = set(conn.scalars(text("SELECT code FROM content.error_tags WHERE active")))
    engine.dispose()

    report = Report()
    rows = read_sheet(args.path, SPEC, report)
    cases = parse_golden(rows, codes, report, read_previous(args.output))
    report.print()
    if not report.ok:
        sys.exit(1)
    counts = {s: sum(1 for c in cases if c.split == s) for s in (DEV, TEST)}
    print(f"{len(cases)} cümle: {counts}")
    if args.apply:
        write_cases(args.output, cases)
        print(f"Yazıldı: {args.output}")
    else:
        print("Deneme (yazılmadı; --apply ile yazılır).")


if __name__ == "__main__":
    main()
