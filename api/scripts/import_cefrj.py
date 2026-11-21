"""CEFR-J Wordlist'i seviye sözlüğüne (`content.vocab_allowlist`) aktarır.

Kaynak: CEFR-J Wordlist Version 1.6, Tono Laboratuvarı, Tokyo Yabancı Diller Üniversitesi
(https://www.cefr-j.org/download.html). Atıfla araştırma ve ticari kullanım serbesttir;
dosya depoya konmaz (yeniden dağıtım açıkça düzenlenmemiş), şuradan indirilir:

    https://www.cefr-j.org/data/CEFRJ_wordlist_ver1.6.zip
    → content/sources/cefrj-1.6/cefrj-wordlist-1.6.xlsx

    cd api
    uv run python -m scripts.import_cefrj [xlsx yolu]

Her kelime en düşük seviyesiyle (A1 < A2 < B1 < B2) bir kez saklanır. Çekimler
lemminflect ile üretilir (went, children, better dahil); doğrulayıcı ayrıca düzenli
ekleri kendisi de çözer. Geliştirme taslak listesi (`source = 'dev-seed'`) silinir.
"""

import os
import sys
from collections.abc import Iterable
from pathlib import Path

from dotenv import load_dotenv
from lemminflect import getAllInflections, getAllInflectionsOOV
from openpyxl import load_workbook
from sqlalchemy import create_engine, text

from scripts.sheets import utf8_output

SOURCE = "cefrj-1.6"
SHEET = "ALL_sep"  # her yazım biçimi ayrı satırda (a.m. / A.M.)
LEVELS = ("A1", "A2", "B1", "B2")
UPOS = {"noun": "NOUN", "verb": "VERB", "adjective": "ADJ", "adverb": "ADV"}
DEFAULT_PATH = (
    Path(__file__).resolve().parents[2] / "content/sources/cefrj-1.6/cefrj-wordlist-1.6.xlsx"
)


def inflections(lemma: str, pos: str) -> set[str]:
    upos = UPOS.get(pos)
    if upos is None or " " in lemma:
        return set()
    table = getAllInflections(lemma, upos=upos) or getAllInflectionsOOV(lemma, upos=upos)
    return {form.lower() for forms in table.values() for form in forms}


def parse_rows(rows: Iterable[tuple[object, ...]]) -> dict[str, tuple[str, set[str]]]:
    """(headword, pos, CEFR, ...) satırlarından kelime → (en düşük seviye, biçimler)."""
    entries: dict[str, tuple[str, set[str]]] = {}
    for row in rows:
        headword, pos, level = (str(v).strip() if v is not None else "" for v in row[:3])
        if not headword or level not in LEVELS:
            continue
        lemma = headword.lower()
        forms = inflections(lemma, pos.lower())
        if lemma in entries:
            old_level, old_forms = entries[lemma]
            level = min(level, old_level, key=LEVELS.index)
            forms |= old_forms
        entries[lemma] = (level, forms)
    return entries


def read_workbook(path: Path) -> dict[str, tuple[str, set[str]]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    rows = workbook[SHEET].iter_rows(values_only=True)
    header = [str(h) for h in next(rows)[:3]]
    if header != ["headword", "pos", "CEFR"]:
        raise ValueError(f"Beklenmeyen başlık: {header}")
    return parse_rows(rows)


def main() -> None:
    utf8_output()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    entries = read_workbook(path)
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    # İçerik şeması uygulama rolüne kapalı: sahip rolüyle yazılır.
    engine = create_engine(os.environ["MIGRATIONS_DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM content.vocab_allowlist WHERE source IN ('dev-seed', :s)"),
            {"s": SOURCE},
        )
        conn.execute(
            text(
                "INSERT INTO content.vocab_allowlist (lemma, cefr, forms, source) "
                "VALUES (:lemma, :cefr, :forms, :source)"
            ),
            [
                {"lemma": lemma, "cefr": level, "forms": sorted(forms - {lemma}), "source": SOURCE}
                for lemma, (level, forms) in sorted(entries.items())
            ],
        )
    engine.dispose()
    by_level = {lvl: sum(1 for lv, _ in entries.values() if lv == lvl) for lvl in LEVELS}
    print(f"{len(entries)} kelime aktarıldı: {by_level}")


if __name__ == "__main__":
    main()
