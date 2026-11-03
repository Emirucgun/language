"""Kural katmanı: müfredat önerisini doğrular, düzeltir ya da reddeder.

Reddedilen öneri bir kez yeniden istenir (hatalar ajana geri verilir); yine geçmezse
deterministik yedek plan kullanılır. Öğrenci her durumda bir plan görür.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.curriculum.schemas import CurriculumDraft, SkillWeights, WeekDraft
from app.validator.core import ValidationResult

WEEKS = 8
STUDY_DAYS_PER_WEEK = 6
MAX_FOCUS_CHARS = 60
MAX_CAN_DO = 3


@dataclass(frozen=True, slots=True)
class PoolItem:
    id: int
    text_en: str
    text_tr: str
    cefr: str


def weekly_capacity(new_per_day: int) -> int:
    return new_per_day * STUDY_DAYS_PER_WEEK


def default_weights(goal: str | None, weak_skills: Sequence[str]) -> SkillWeights:
    """Hedef ve zayıf beceriye göre başlangıç ağırlıkları (toplam 1)."""
    raw = {"vocabulary": 0.3, "reading": 0.25, "listening": 0.2, "writing": 0.25}
    if goal == "daily_conversation":
        raw["writing"] += 0.1  # yazılı diyalog yazma ağırlığında
    for skill in weak_skills:
        if skill in raw:
            raw[skill] += 0.1
    total = sum(raw.values())
    return SkillWeights(**{k: round(v / total, 2) for k, v in raw.items()})


def _normalize(weights: SkillWeights) -> SkillWeights:
    values = weights.model_dump()
    total = sum(values.values())
    if total <= 0:
        return SkillWeights(vocabulary=0.25, reading=0.25, listening=0.25, writing=0.25)
    return SkillWeights(**{k: round(v / total, 2) for k, v in values.items()})


def validate(
    draft: CurriculumDraft, pool: Sequence[PoolItem], capacity: int
) -> tuple[ValidationResult, CurriculumDraft]:
    """Sert kurallar ret sebebidir; küçük kusurlar (ağırlık toplamı, fazla madde) düzeltilir."""
    result = ValidationResult()
    pool_ids = {p.id for p in pool}
    weeks = sorted(draft.weeks, key=lambda w: w.week)

    if [w.week for w in weeks] != list(range(1, WEEKS + 1)):
        result.add("weeks", f"haftalar 1–{WEEKS} olmalı: {[w.week for w in weeks]}")
    seen: set[int] = set()
    for w in weeks:
        unknown = [i for i in w.item_ids if i not in pool_ids]
        if unknown:
            result.add("unknown_items", f"hafta {w.week}: {unknown}")
        repeated = [i for i in w.item_ids if i in seen]
        if repeated:
            result.add("repeated_items", f"hafta {w.week}: {repeated}")
        seen.update(w.item_ids)
        if len(w.item_ids) > capacity:
            result.add("too_many_items", f"hafta {w.week}: {len(w.item_ids)} > {capacity}")
        if not w.focus_tr.strip():
            result.add("missing_focus", f"hafta {w.week}")
        if not w.can_do_tr:
            result.add("missing_can_do", f"hafta {w.week}")
    # Havuz yettiği sürece boş hafta olmasın.
    if len(seen) < min(len(pool_ids), capacity * WEEKS) * 0.8:
        result.add("low_coverage", f"{len(seen)} öğe planlandı, havuz {len(pool_ids)}")

    fixed = CurriculumDraft(
        summary_tr=draft.summary_tr.strip()[:300],
        weeks=[
            WeekDraft(
                week=w.week,
                focus_tr=w.focus_tr.strip()[:MAX_FOCUS_CHARS],
                item_ids=list(w.item_ids),
                can_do_tr=[c.strip() for c in w.can_do_tr if c.strip()][:MAX_CAN_DO],
                skill_weights=_normalize(w.skill_weights),
            )
            for w in weeks
        ],
    )
    return result, fixed


def fallback(pool: Sequence[PoolItem], capacity: int, weights: SkillWeights) -> CurriculumDraft:
    """LLM'siz plan: havuz sırasını haftalara böler. Her zaman geçerlidir."""
    weeks = []
    for index in range(WEEKS):
        chunk = pool[index * capacity : (index + 1) * capacity]
        weeks.append(
            WeekDraft(
                week=index + 1,
                focus_tr=f"Hafta {index + 1}: yeni kelime ve kalıplar"
                if chunk
                else f"Hafta {index + 1}: tekrar",
                item_ids=[p.id for p in chunk],
                can_do_tr=(
                    [f"“{chunk[0].text_en}” ve benzer ifadeleri basit cümlelerde kullanabilirim."]
                    if chunk
                    else ["Öğrendiklerimi kısa cümlelerde rahatça kullanabilirim."]
                ),
                skill_weights=weights,
            )
        )
    return CurriculumDraft(
        summary_tr="Plan, seçilen kelime ve kalıpları haftalara dengeli dağıtır.",
        weeks=weeks,
    )
