"""Müfredat ajanı: öneri (Sonnet) → kural doğrulaması → kayıt.

`ensure_curriculum` kullanıcının güncel müfredatını döndürür; yoksa oluşturur. Ajan bir
kez reddedilirse hatalar kendisine geri verilip bir kez daha sorulur; yine geçmezse
deterministik yedek plan kaydedilir. Her plan yeni bir sürümdür ve olay kaydına yazılır.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import Item
from app.curriculum.models import Curriculum
from app.curriculum.rules import (
    WEEKS,
    PoolItem,
    default_weights,
    fallback,
    validate,
    weekly_capacity,
)
from app.curriculum.schemas import CurriculumDraft, CurriculumView, SkillWeights, WeekView
from app.events.models import Event
from app.events.service import record_event
from app.llm.client import LLMClient
from app.llm.prompts import render_static
from app.llm.service import DailyLimitExceeded, Prompt, generate_structured
from app.llm.snapshot import daily_snapshot
from app.onboarding.fixed_tests import user_level

PROMPT_VERSION = "v1"


def _new_per_day(daily_minutes: int | None) -> int:
    """Günde yeni öğe; oturum üretimindeki kotayla aynı (sessions.generation._quotas)."""
    minutes = daily_minutes or 15
    if minutes <= 10:
        return 2
    if minutes <= 20:
        return 3
    return 4


def pool_for(db: Session, start_level: str) -> list[PoolItem]:
    """Öğretilebilecek öğeler; öğrencinin seviyesindekiler önce."""
    items = list(
        db.scalars(
            select(Item)
            .where(Item.active, Item.cefr.in_(("A1", "A2")))
            .order_by(Item.sublevel.nulls_last(), Item.id)
        )
    )
    first = [i for i in items if i.cefr == start_level]
    rest = [i for i in items if i.cefr != start_level]
    return [PoolItem(i.id, i.text_en, i.text_tr, i.cefr) for i in first + rest]


def _weak_skills(db: Session, user_id: uuid.UUID) -> list[str]:
    payload = db.scalar(
        select(Event.payload)
        .where(Event.user_id == user_id, Event.type == "goal_set")
        .order_by(Event.id.desc())
        .limit(1)
    )
    skills = (payload or {}).get("weak_skills") or []
    return [str(s) for s in skills]


def _task(pool: list[PoolItem], capacity: int, issues: list[str] | None) -> str:
    lines = [
        f"Weekly capacity (max new items per week): {capacity}",
        f"Pool size: {len(pool)}",
        "Item pool (id | English | Turkish | level):",
        *(f"{p.id} | {p.text_en} | {p.text_tr} | {p.cefr}" for p in pool),
    ]
    if issues:
        lines += ["", "Your previous plan was rejected for these reasons; fix them:", *issues]
    return "\n".join(lines)


def latest(db: Session, user_id: uuid.UUID) -> Curriculum | None:
    return db.scalar(
        select(Curriculum)
        .where(Curriculum.user_id == user_id)
        .order_by(Curriculum.version.desc())
        .limit(1)
    )


def ensure_curriculum(
    db: Session, client: LLMClient, user: User, *, reason: str = "initial"
) -> Curriculum:
    existing = latest(db, user.id)
    if existing is not None and reason == "initial":
        return existing

    start_level, _ = user_level(db, user.id)
    pool = pool_for(db, start_level)
    capacity = weekly_capacity(_new_per_day(user.daily_minutes))
    weights = default_weights(user.goal, _weak_skills(db, user.id))
    snapshot = daily_snapshot(db, user.id)

    plan: CurriculumDraft | None = None
    call_id: int | None = None
    issues: list[str] | None = None
    for _ in range(2):
        prompt = Prompt(
            purpose="curriculum",
            prompt_version=PROMPT_VERSION,
            static_block=render_static("curriculum", PROMPT_VERSION),
            snapshot_id=snapshot.id,
            snapshot_block=snapshot.text,
            task=_task(pool, capacity, issues),
        )
        try:
            draft, call = generate_structured(
                db, client, prompt=prompt, output_type=CurriculumDraft, user_id=user.id
            )
        except DailyLimitExceeded:
            break
        call_id = call.id
        if draft is None:
            break
        result, fixed = validate(draft, pool, capacity)
        if result.ok:
            plan = fixed
            break
        issues = [f"- {i.code}: {i.detail}" for i in result.issues]

    source = "agent"
    if plan is None:
        plan, source, call_id = fallback(pool, capacity, weights), "fallback", None

    version = (existing.version + 1) if existing else 1
    curriculum = Curriculum(
        user_id=user.id,
        version=version,
        weeks=[w.model_dump() for w in plan.weeks],
        # Plan düzeyi: genel ağırlıklar, özet ve kaynak (agent | fallback); haftalık ağırlıklar
        # `weeks` içinde.
        skill_weights={
            "overall": weights.model_dump(),
            "summary_tr": plan.summary_tr,
            "source": source,
        },
        change_reason=reason,
        llm_call_id=call_id,
    )
    db.add(curriculum)
    db.flush()
    record_event(
        db,
        user_id=user.id,
        type="curriculum_created" if version == 1 else "curriculum_replanned",
        payload={},
    )
    return curriculum


def current_week(curriculum: Curriculum, now: datetime | None = None) -> int:
    elapsed = (now or datetime.now(UTC)) - curriculum.created_at
    return min(WEEKS, max(1, elapsed.days // 7 + 1))


def new_item_order(curriculum: Curriculum, now: datetime | None = None) -> list[int]:
    """Yeni öğe sırası: bu haftanın öğeleri, sonra sonraki haftalar, en son önceki haftalar
    (geride kalan öğrenci kaçırdıklarını da görsün)."""
    week = current_week(curriculum, now)
    weeks = sorted(curriculum.weeks, key=lambda w: w["week"])
    ahead = [i for w in weeks if w["week"] >= week for i in w["item_ids"]]
    behind = [i for w in weeks if w["week"] < week for i in w["item_ids"]]
    return ahead + behind


def view(db: Session, curriculum: Curriculum) -> CurriculumView:
    week_now = current_week(curriculum)
    texts = dict(db.execute(select(Item.id, Item.text_en)).tuples().all())
    weeks = [
        WeekView(
            week=w["week"],
            focus_tr=w["focus_tr"],
            can_do_tr=w["can_do_tr"],
            item_count=len(w["item_ids"]),
            items_en=[texts[i] for i in w["item_ids"] if i in texts],
            current=w["week"] == week_now,
            skill_weights=SkillWeights.model_validate(w["skill_weights"]),
        )
        for w in sorted(curriculum.weeks, key=lambda w: w["week"])
    ]
    return CurriculumView(
        version=curriculum.version,
        summary_tr=str(curriculum.skill_weights.get("summary_tr", "")),
        weeks=weeks,
        current_week=week_now,
        estimate_tr=(
            f"Yaklaşık {WEEKS} hafta, günde birkaç yeni öğe. Bu bir tahmin: hızın ve "
            "tekrarlarına göre plan her hafta güncellenir."
        ),
    )
