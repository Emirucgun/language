"""Doğrulayıcının ortak parçaları: sonuç tipi, sözcükleme ve seviye sözlüğü.

Doğrulayıcı deterministiktir ve LLM kullanmaz. Geçemeyen çıktı öğrenciye gitmez;
sonuç (`to_dict`) üretilen içerikle birlikte `validator_result` olarak saklanır.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.models import Item, VocabAllowlist

VALIDATOR_VERSION = "v1"

_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    detail: str


@dataclass(slots=True)
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, code: str, detail: str) -> None:
        self.issues.append(Issue(code, detail))

    def to_dict(self) -> dict[str, object]:
        return {
            "version": VALIDATOR_VERSION,
            "ok": self.ok,
            "issues": [{"code": i.code, "detail": i.detail} for i in self.issues],
        }


def words(text: str) -> list[str]:
    """İngilizce kelimeler, küçük harfle; sayılar ve noktalama atlanır."""
    return [w.lower() for w in _WORD.findall(text)]


def _proper_nouns(text: str) -> set[str]:
    """Cümle başı olmayan büyük harfli kelimeler (Paris, Ali) seviye kontrolünden muaf."""
    names: set[str] = set()
    for sentence in re.split(r"[.!?]\s+", text):
        for token in _WORD.findall(sentence)[1:]:
            if token[0].isupper() and token.lower() != "i":
                names.add(token.lower())
    return names


def base_forms(word: str) -> set[str]:
    """Düzenli çekimlerden olası kök biçimler: friends→friend, watching→watch, lived→live.

    Bilerek basit: yalnızca düzenli -s/-es/-ies, -ing, -ed, -er/-est. Düzensiz biçimler
    (went, children) listede açıkça bulunmalı. Fazla aday üretmek zararsız; yalnızca
    sözlükte olanlar kabul edilir.
    """
    candidates = {word, word.split("'")[0]}  # don't, it's, Ali's
    for suffix, replacements in (
        ("ies", ("y",)),
        ("es", ("", "e")),
        ("s", ("",)),
        ("ied", ("y",)),
        ("ed", ("", "e")),
        ("ing", ("", "e")),
        ("est", ("", "e")),
        ("er", ("", "e")),
    ):
        if word.endswith(suffix) and len(word) >= len(suffix) + 2:  # kök en az 2 harf: goes→go
            stem = word[: -len(suffix)]
            candidates.update(stem + r for r in replacements)
            # Çift ünsüz: running→run, stopped→stop, bigger→big
            if len(stem) >= 3 and stem[-1] == stem[-2]:
                candidates.add(stem[:-1])
    return candidates


@dataclass(frozen=True, slots=True)
class Lexicon:
    """Seviyeye izin verilen tüm biçimler (lemma + çekimler)."""

    forms: frozenset[str]

    def out_of_level(self, text: str, also_allowed: Iterable[str] = ()) -> list[str]:
        allowed = self.forms | {w.lower() for w in also_allowed} | _proper_nouns(text)
        unknown: list[str] = []
        for word in words(text):
            if allowed.isdisjoint(base_forms(word)) and word not in unknown:
                unknown.append(word)
        return unknown


def load_lexicon(session: Session, levels: tuple[str, ...] = ("A1", "A2")) -> Lexicon:
    forms: set[str] = set()
    for lemma, extra in session.execute(
        select(VocabAllowlist.lemma, VocabAllowlist.forms).where(VocabAllowlist.cefr.in_(levels))
    ):
        forms.add(lemma.lower())
        forms.update(words(lemma))  # çok kelimeli girdiler: "a lot" → a, lot
        forms.update(f.lower() for f in extra)
    for text_en, extra in session.execute(
        select(Item.text_en, Item.forms).where(Item.cefr.in_(levels), Item.active)
    ):
        forms.update(words(text_en))
        forms.update(f.lower() for f in extra)
    return Lexicon(frozenset(forms))
