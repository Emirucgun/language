"""Işıl'ın tablolarını `content/templates/` altına üretir.

    cd api
    uv run python -m scripts.make_templates

Dosyalar Google Drive'a yüklenip Sheets olarak açılır. Hata etiketleri ve yerleştirme
incelemesi mevcut taslak içerikle önceden doldurulur.
"""

from pathlib import Path

from app.onboarding.placement import FixedQuestion
from scripts import import_error_tags, import_golden, import_items, import_placement
from scripts.dev_content import ERROR_TAGS
from scripts.placement_form_b import QUESTIONS as FORM_B
from scripts.placement_v1 import QUESTIONS
from scripts.sheets import utf8_output, write_template

OUTPUT = Path(__file__).resolve().parents[2] / "content/templates"


def main(output: Path = OUTPUT) -> None:
    utf8_output()
    tags = [
        {"code": code, "name": name, "explanation": explanation, "active": "Evet"}
        for code, name, explanation in ERROR_TAGS
    ]
    def rows(bank: list[dict[str, object]]) -> list[dict[str, str]]:
        return [import_placement.question_row(FixedQuestion.model_validate(q)) for q in bank]

    write_template(output / import_items.SPEC.file_name, import_items.SPEC)
    write_template(output / import_golden.SPEC.file_name, import_golden.SPEC)
    write_template(output / import_error_tags.SPEC.file_name, import_error_tags.SPEC, tags)
    write_template(output / import_placement.SPEC.file_name, import_placement.SPEC, rows(QUESTIONS))
    write_template(
        output / import_placement.SPEC_B.file_name, import_placement.SPEC_B, rows(FORM_B)
    )
    print(f"Şablonlar yazıldı: {output}")


if __name__ == "__main__":
    main()
