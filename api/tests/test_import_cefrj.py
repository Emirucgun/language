"""CEFR-J içe aktarma: satır ayrıştırma ve çekimler (dosyaya ihtiyaç duymaz)."""

from scripts.import_cefrj import parse_rows

ROWS = [
    ("go", "verb", "A1", None, None, None),
    ("child", "noun", "A1", None, None, None),
    ("light", "noun", "A1", None, None, None),
    ("light", "adjective", "A2", None, None, None),
    ("a lot", "pronoun", "A1", None, None, None),
    ("jazz", "noun", "B1", None, None, None),
    ("ignored", "noun", "C1", None, None, None),
    (None, None, None, None, None, None),
]


def test_irregular_forms_come_from_lemminflect() -> None:
    entries = parse_rows(ROWS)
    assert {"went", "gone", "goes", "going"} <= entries["go"][1]
    assert "children" in entries["child"][1]


def test_lowest_level_wins_and_forms_merge() -> None:
    level, forms = parse_rows(ROWS)["light"]
    assert level == "A1"
    assert {"lights", "lighter"} <= forms  # isim + sıfat çekimleri birleşir


def test_multiword_and_unknown_levels() -> None:
    entries = parse_rows(ROWS)
    assert entries["a lot"] == ("A1", set())
    assert entries["jazz"][0] == "B1"
    assert "ignored" not in entries
