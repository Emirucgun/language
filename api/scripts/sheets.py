"""Işıl'ın tablolarının ortak altyapısı: sütun tanımı, şablon yazma, okuma, doğrulama raporu.

Sütunlar tek yerde (`Spec`) tanımlanır: hem şablon hem içe aktarma aynı tanımı kullanır,
böylece ikisi birbirinden kopamaz. Google Sheets'ten `.xlsx` olarak indirilen dosya okunur.

Betikler varsayılan olarak yalnızca rapor verir; yazmak için `--apply` gerekir. Tek bir hata
bile varsa hiçbir satır yazılmaz.
"""

import io
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import Engine, create_engine

DATA_SHEET = "Veri"
GUIDE_SHEET = "Açıklama"
MULTI_SEPARATOR = "|"
TEMPLATE_ROWS = 1000  # açılır liste bu satıra kadar uygulanır


@dataclass(frozen=True, slots=True)
class Column:
    key: str
    header: str
    help: str
    required: bool = False
    choices: tuple[str, ...] = ()
    width: int = 22


@dataclass(frozen=True, slots=True)
class Spec:
    title: str
    file_name: str
    columns: tuple[Column, ...]
    guide: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Row:
    number: int  # tablodaki satır numarası: Işıl'ın gördüğü sayı
    values: dict[str, str]

    def __getitem__(self, key: str) -> str:
        return self.values.get(key, "")


@dataclass(slots=True)
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, row: int | None, message: str) -> None:
        self.errors.append(_line(row, message))

    def warn(self, row: int | None, message: str) -> None:
        self.warnings.append(_line(row, message))

    def print(self) -> None:
        for line in self.errors:
            print(f"HATA   {line}")
        for line in self.warnings:
            print(f"UYARI  {line}")
        print(f"{len(self.errors)} hata, {len(self.warnings)} uyarı.")


def utf8_output() -> None:
    """Windows'ta çıktı yönlendirilince cp1252 olur ve Türkçe rapor yazdırılamaz."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")


def _line(row: int | None, message: str) -> str:
    return f"satır {row}: {message}" if row is not None else message


def split_multi(value: str) -> list[str]:
    """`a | b | c` hücresini listeye çevirir; düzeltmelerde virgül geçebildiği için `|`."""
    return [part.strip() for part in value.split(MULTI_SEPARATOR) if part.strip()]


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Evet" if value else "Hayır"
    return str(value).strip()


def turkish_fold(value: str) -> str:
    """Türkçe harf kurallarıyla küçültür: `casefold` I'yı i, İ'yi iki karakter yapar."""
    return value.replace("I", "ı").replace("İ", "i").casefold()


def _canonical(value: str, choices: tuple[str, ...]) -> str | None:
    folded = turkish_fold(value)
    return next((c for c in choices if turkish_fold(c) == folded), None)


def read_sheet(path: Path, spec: Spec, report: Report) -> list[Row]:
    """Satırları okur; zorunlu alan ve açılır liste kontrollerini burada yapar."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    if DATA_SHEET not in workbook.sheetnames:
        report.error(None, f"'{DATA_SHEET}' sayfası yok: {workbook.sheetnames}")
        return []
    table = workbook[DATA_SHEET].iter_rows(values_only=True)
    header = [_text(h) for h in next(table, ())]
    missing = [c.header for c in spec.columns if c.header not in header]
    if missing:
        report.error(None, f"eksik sütun: {', '.join(missing)}")
        return []
    positions = {c.key: header.index(c.header) for c in spec.columns}

    rows: list[Row] = []
    for number, cells in enumerate(table, start=2):
        texts = [_text(cell) for cell in cells]
        if not any(texts):
            continue
        values = {k: texts[i] if i < len(texts) else "" for k, i in positions.items()}
        for column in spec.columns:
            value = values[column.key]
            if not value:
                if column.required:
                    report.error(number, f"{column.header} boş")
            elif column.choices:
                canonical = _canonical(value, column.choices)
                if canonical is None:
                    allowed = ", ".join(column.choices)
                    report.error(number, f"{column.header} '{value}' geçersiz ({allowed})")
                else:
                    values[column.key] = canonical
        rows.append(Row(number, values))
    workbook.close()
    return rows


def write_template(path: Path, spec: Spec, rows: list[dict[str, str]] | None = None) -> None:
    """Boş ya da önceden doldurulmuş şablon; Sheets açılır listeleri korur."""
    workbook = Workbook()
    data = workbook.active
    assert data is not None
    data.title = DATA_SHEET
    data.append([c.header for c in spec.columns])
    for values in rows or []:
        data.append([values.get(c.key, "") for c in spec.columns])

    fill = PatternFill("solid", fgColor="DDE7F3")
    for index, column in enumerate(spec.columns, start=1):
        letter = get_column_letter(index)
        cell = data.cell(row=1, column=index)
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        data.column_dimensions[letter].width = column.width
        if column.choices:
            options = ",".join(column.choices)
            validation = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
            validation.error = f"Seçenekler: {', '.join(column.choices)}"
            data.add_data_validation(validation)
            validation.add(f"{letter}2:{letter}{TEMPLATE_ROWS}")
    data.freeze_panes = "A2"

    guide = workbook.create_sheet(GUIDE_SHEET)
    guide.append([spec.title])
    guide["A1"].font = Font(bold=True, size=13)
    for line in spec.guide:
        guide.append([line])
    guide.append([])
    guide.append(["Sütun", "Zorunlu", "Seçenekler", "Açıklama"])
    for cell in guide[guide.max_row]:
        cell.font = Font(bold=True)
    for column in spec.columns:
        guide.append(
            [
                column.header,
                "Evet" if column.required else "Hayır",
                ", ".join(column.choices),
                column.help,
            ]
        )
    for letter, width in zip("ABCD", (30, 10, 28, 90), strict=True):
        guide.column_dimensions[letter].width = width

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def owner_engine() -> Engine:
    """İçerik şeması uygulama rolüne kapalı: sahip rolüyle yazılır."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    return create_engine(os.environ["MIGRATIONS_DATABASE_URL"])


def contains_term(sentence: str, terms: list[str]) -> bool:
    """Terimlerden biri cümlede tam kelime olarak geçiyor mu?"""
    return any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", sentence, re.IGNORECASE) for term in terms
    )
