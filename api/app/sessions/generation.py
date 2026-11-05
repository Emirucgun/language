"""Bugünün oturumu: seçim kural katmanında, içerik LLM'de (docs/architecture/flows.md).

    tekrar motoru öğeleri seçer → paylaşılabilir içerik varsa yeniden kullanılır
    → kalanlar için tek Haiku çağrısı → her etkinlik ayrı doğrulanır
    → kalanlar bir kez yeniden üretilir → yine kalırsa şablona düşer → kayıt

Üretilen her şey (reddedilen dahil) `activity_contents`'te saklanır; öğrenciye yalnızca
onaylı içerik `activities` olarak bağlanır. Commit çağırana aittir.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import Item
from app.curriculum.service import ensure_curriculum, new_item_order
from app.events.schemas import known_interests
from app.llm.client import LLMClient
from app.llm.prompts import render_static
from app.llm.purposes import Purpose
from app.llm.service import DailyLimitExceeded, Prompt, generate_structured
from app.llm.snapshot import daily_snapshot
from app.onboarding.fixed_tests import user_level
from app.scheduler.quotas import daily_quota
from app.scheduler.service import lock_user, select_items
from app.sessions.models import Activity, ActivityContent, StudySession
from app.sessions.schemas import ActivityModel, Kind, SessionOutput
from app.sessions.templates import recall_from_card, writing_from_card
from app.sessions.validation import (
    ItemCard,
    validate_new_item,
    validate_reading,
    validate_recall,
    validate_writing,
)
from app.validator.core import VALIDATOR_VERSION, Lexicon, ValidationResult, load_lexicon

PROMPT_VERSION = "v3"  # v3: 4 şık, doğru cevap sabit yerde değil
SHAREABLE_KINDS = ("recall", "new_item")
ORDER: dict[Kind, int] = {"new_item": 0, "recall": 1, "reading": 2, "writing": 3}
READING = 0  # okuma tek öğeye bağlı değil; eksik listesinde bu anahtarla tutulur

Wanted = set[tuple[Kind, int]]


@dataclass(frozen=True, slots=True)
class SessionPlan:
    review: list[ItemCard]
    new: list[ItemCard]
    reading: list[ItemCard]  # boşsa okuma yok
    writing: list[ItemCard]
    cefr_sub: str = "A1.1"  # yerleştirme testinden; paylaşılan içerik bununla eşleşir


@dataclass(slots=True)
class Final:
    kind: Kind
    item_ids: list[int]
    origin: str  # session | template
    activity: ActivityModel | None = None  # yeniden kullanımda None
    validation: ValidationResult = field(default_factory=ValidationResult)
    call_id: int | None = None
    content_id: int | None = None  # yeniden kullanılan içerik


@dataclass(slots=True)
class Round:
    """Bir üretim turu: onaylananlar, reddedilenler, hâlâ eksik olanlar."""

    accepted: list[Final] = field(default_factory=list)
    rejected: list[Final] = field(default_factory=list)
    missing: Wanted = field(default_factory=set)


def _card(item: Item) -> ItemCard:
    return ItemCard(item.id, item.text_en, item.text_tr, tuple(item.forms))


def plan_session(
    db: Session, user: User, local_date: date, curriculum_order: list[int] | None = None
) -> SessionPlan:
    quota = daily_quota(user.daily_minutes)
    start_level, cefr_sub = user_level(db, user.id)
    items = list(
        db.scalars(
            select(Item)
            .where(Item.active, Item.cefr.in_(("A1", "A2")))
            .order_by(Item.sublevel.nulls_last(), Item.id)
        )
    )
    by_id = {i.id: _card(i) for i in items}
    # Yeni öğe sırası müfredattan (bu haftadan başlayarak). Müfredat yoksa havuz sırası:
    # A1 öğrencisine yalnızca A1 öğeleri; A2 öğrencisine önce A2, sonra A1 öğeleri.
    level_order = [i.id for i in items if i.cefr == start_level]
    if start_level == "A2":
        level_order += [i.id for i in items if i.cefr == "A1"]
    planned = [i for i in (curriculum_order or []) if i in by_id]
    new_order = planned or level_order
    end_of_day = datetime.combine(local_date + timedelta(days=1), time.min, ZoneInfo(user.timezone))
    selection = select_items(
        db,
        user.id,
        due_before=end_of_day,
        candidate_new_ids=new_order,
        max_reviews=quota.max_reviews,
        max_new=quota.max_new,
    )
    review = [by_id[i] for i in selection.review_item_ids if i in by_id]
    new = [by_id[i] for i in selection.new_item_ids]
    today = new + review
    return SessionPlan(
        review=review,
        new=new,
        reading=today[:4] if len(today) >= 2 else [],
        writing=today[:1],
        cefr_sub=cefr_sub,
    )


def _all_cards(plan: SessionPlan) -> list[ItemCard]:
    """Plandaki tüm öğeler (yeniden kullanılanlar çıkarılsa da yazma/okuma öğeleri kalır)."""
    unique = {c.id: c for c in plan.review + plan.new + plan.writing + plan.reading}
    return list(unique.values())


def _interest_tag(user: User) -> str | None:
    known = known_interests(user.interests)
    return known[0] if known else None


def _reusable(db: Session, user: User, kind: Kind, card: ItemCard, cefr_sub: str) -> int | None:
    """Başka bir kullanıcı için üretilmiş, onaylı ve bu kullanıcının görmediği içerik."""
    seen = select(Activity.content_id).where(Activity.user_id == user.id)
    return db.scalar(
        select(ActivityContent.id)
        .where(
            ActivityContent.kind == kind,
            ActivityContent.status == "approved",
            ActivityContent.shareable,
            ActivityContent.item_ids == [card.id],
            ActivityContent.cefr_sub == cefr_sub,
            ActivityContent.interest_tag.is_not_distinct_from(_interest_tag(user)),
            ActivityContent.id.not_in(seen),
        )
        .order_by(ActivityContent.id)
        .limit(1)
    )


def _cards_text(cards: list[ItemCard]) -> str:
    return "; ".join(f'[{c.id}] "{c.text_en}" ({c.text_tr})' for c in cards) or "none"


def _task(user: User, plan: SessionPlan) -> str:
    interests = ", ".join(known_interests(user.interests)) or "none"
    return "\n".join(
        [
            f"Learner goal: {user.goal or 'unspecified'}; interests: {interests}",
            f"recall for: {_cards_text(plan.review)}",
            f"new_item for: {_cards_text(plan.new)}",
            f"reading using: {_cards_text(plan.reading) if plan.reading else 'not requested'}",
            f"writing for: {_cards_text(plan.writing) if plan.writing else 'not requested'}",
        ]
    )


def _wanted(plan: SessionPlan) -> Wanted:
    wanted: Wanted = {("recall", c.id) for c in plan.review}
    wanted |= {("new_item", c.id) for c in plan.new}
    wanted |= {("writing", c.id) for c in plan.writing}
    if plan.reading:
        wanted.add(("reading", READING))
    return wanted


def _check(output: SessionOutput, plan: SessionPlan, lexicon: Lexicon, call_id: int) -> Round:
    """Her etkinliği ayrı doğrular; gelmeyen ya da kalan (tür, öğe) çiftleri eksiktir."""
    result = Round(missing=_wanted(plan))

    def judge(kind: Kind, activity: ActivityModel, items: list[int], v: ValidationResult) -> None:
        final = Final(kind, items, "session", activity, v, call_id)
        if v.ok:
            result.accepted.append(final)
            result.missing.discard((kind, READING if kind == "reading" else items[0]))
        else:
            result.rejected.append(final)

    cards = {c.id: c for c in _all_cards(plan)}
    for recall in output.recall:
        if ("recall", recall.item_id) in result.missing:
            card = cards[recall.item_id]
            judge("recall", recall, [card.id], validate_recall(recall, card, lexicon))
    for new in output.new_items:
        if ("new_item", new.item_id) in result.missing:
            card = cards[new.item_id]
            judge("new_item", new, [card.id], validate_new_item(new, card, lexicon))
    for writing in output.writing:
        if ("writing", writing.item_id) in result.missing:
            judge(
                "writing",
                writing,
                [writing.item_id],
                validate_writing(writing, cards[writing.item_id]),
            )
    if plan.reading and output.reading:
        reading = output.reading[0]
        items = [i for i in reading.item_ids if i in cards]
        judge("reading", reading, items, validate_reading(reading, plan.reading, lexicon))
    return result


def _round(
    db: Session,
    client: LLMClient,
    user: User,
    plan: SessionPlan,
    snapshot_id: int,
    snapshot_text: str,
    lexicon: Lexicon,
    purpose: Purpose = "session",
) -> Round:
    prompt = Prompt(
        purpose=purpose,
        prompt_version=PROMPT_VERSION,
        static_block=render_static("session", PROMPT_VERSION),
        snapshot_id=snapshot_id,
        snapshot_block=snapshot_text,
        task=_task(user, plan),
    )
    try:
        output, call = generate_structured(
            db, client, prompt=prompt, output_type=SessionOutput, user_id=user.id
        )
    except DailyLimitExceeded:
        return Round(missing=_wanted(plan))
    if output is None:
        return Round(missing=_wanted(plan))
    return _check(output, plan, lexicon, call.id)


def _narrow(plan: SessionPlan, missing: Wanted) -> SessionPlan:
    return SessionPlan(
        review=[c for c in plan.review if ("recall", c.id) in missing],
        new=[c for c in plan.new if ("new_item", c.id) in missing],
        reading=plan.reading if ("reading", READING) in missing else [],
        writing=[c for c in plan.writing if ("writing", c.id) in missing],
        cefr_sub=plan.cefr_sub,
    )


def _store_content(
    db: Session, final: Final, user: User, cefr_sub: str, status: str, salt: str = ""
) -> int:
    assert final.activity is not None
    canonical = json.dumps(final.activity.model_dump(), sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(f"{final.kind}|{salt}|{canonical}".encode()).digest()
    db.execute(
        insert(ActivityContent)
        .values(
            content_hash=digest,
            kind=final.kind,
            item_ids=final.item_ids,
            cefr_sub=cefr_sub,
            interest_tag=_interest_tag(user),
            content=final.activity.model_dump(),
            model="llm" if final.call_id else None,
            prompt_version=PROMPT_VERSION if final.call_id else None,
            validator_version=VALIDATOR_VERSION,
            validator_result=final.validation.to_dict(),
            status=status,
            shareable=status == "approved" and final.kind in SHAREABLE_KINDS and not salt,
            llm_call_id=final.call_id,
        )
        .on_conflict_do_nothing(index_elements=["content_hash"])
    )
    content_id = db.scalar(select(ActivityContent.id).where(ActivityContent.content_hash == digest))
    assert content_id is not None
    return content_id


def _distractors(db: Session) -> list[ItemCard]:
    """Şablon çeldiricileri havuzdan: plandaki birkaç öğe dört şıka yetmez."""
    items = db.scalars(select(Item).where(Item.active, Item.cefr.in_(("A1", "A2"))))
    return [_card(item) for item in items]


def _templates(plan: SessionPlan, missing: Wanted, distractors: list[ItemCard]) -> list[Final]:
    """Hâlâ eksik olanlar için şablon. Okuma için şablon yok; oturumdan çıkar."""
    cards = _all_cards(plan)
    finals: list[Final] = []
    for kind, item_id in sorted(missing):
        if kind == "reading":
            continue
        card = next(c for c in cards if c.id == item_id)
        activity: ActivityModel | None = (
            writing_from_card(card) if kind == "writing" else recall_from_card(card, distractors)
        )
        if activity is None:
            continue  # çeldirici yetmedi: az şıklı soru yerine soru yok
        finals.append(
            Final("writing" if kind == "writing" else "recall", [card.id], "template", activity)
        )
    return finals


def ensure_session(
    db: Session, client: LLMClient, user: User, local_date: date, *, lexicon: Lexicon | None = None
) -> StudySession:
    """Bugünün oturumunu döndürür; yoksa üretir. Aynı gün ikinci çağrı LLM'e gitmez."""
    lock_user(db, user.id)
    study = db.scalar(
        select(StudySession).where(
            StudySession.user_id == user.id, StudySession.local_date == local_date
        )
    )
    if study is not None and study.status in ("ready", "completed"):
        return study
    if study is None:
        study = StudySession(user_id=user.id, local_date=local_date)
        db.add(study)
        db.flush()

    curriculum = ensure_curriculum(db, client, user)
    full_plan = plan_session(db, user, local_date, new_item_order(curriculum))
    snapshot = daily_snapshot(db, user.id)
    study.snapshot_id = snapshot.id
    build_activities(
        db,
        client,
        user,
        full_plan,
        lexicon=lexicon,
        origin="session",
        session_id=study.id,
        recommended=True,
        # Şablonlar aynı öğe için tekrar eder; kullanıcı + gün ile ayrı içerik sayılır.
        template_salt=f"template:{user.id}:{local_date}",
    )
    study.status = "ready"
    db.flush()
    return study


def build_activities(
    db: Session,
    client: LLMClient,
    user: User,
    full_plan: SessionPlan,
    *,
    lexicon: Lexicon | None,
    origin: str,
    session_id: int | None,
    recommended: bool,
    template_salt: str,
    purpose: Purpose = "session",
) -> list[int]:
    """Plan → etkinlikler: yeniden kullanım, üretim, bir kez daha, şablon, kayıt.

    Bugünün oturumu ve ek çalışma aynı yoldan geçer. Etkinlik id'lerini sırayla döner.
    """
    snapshot = daily_snapshot(db, user.id)
    lexicon = lexicon or load_lexicon(db)

    # 1. Yeniden kullanım: kısa türlerde başkası için üretilmiş onaylı içerik.
    finals: list[Final] = []
    review: list[ItemCard] = []
    new: list[ItemCard] = []
    for kind, cards, keep in (
        ("recall", full_plan.review, review),
        ("new_item", full_plan.new, new),
    ):
        for card in cards:
            reused = _reusable(db, user, kind, card, full_plan.cefr_sub)  # type: ignore[arg-type]
            if reused is None:
                keep.append(card)
            else:
                finals.append(Final(kind, [card.id], "session", content_id=reused))  # type: ignore[arg-type]
    plan = SessionPlan(review, new, full_plan.reading, full_plan.writing, full_plan.cefr_sub)

    # 2. Üretim, 3. kalanlar için bir kez daha, 4. şablon.
    rejected: list[Final] = []
    missing = _wanted(plan)
    for _ in range(2):
        if not missing:
            break
        result = _round(
            db, client, user, _narrow(plan, missing), snapshot.id, snapshot.text, lexicon, purpose
        )
        finals += result.accepted
        rejected += result.rejected
        if result.missing == missing and not result.accepted and not result.rejected:
            break  # çağrı hiç yapılamadı (limit/hata): tekrar denemenin anlamı yok
        missing = result.missing
    finals += _templates(plan, missing, _distractors(db) if missing else [])

    for final in rejected:
        _store_content(db, final, user, plan.cefr_sub, "rejected")

    finals.sort(key=lambda f: ORDER[f.kind])
    activity_ids: list[int] = []
    for position, final in enumerate(finals):
        salt = template_salt if final.origin == "template" else ""
        content_id = final.content_id or _store_content(
            db, final, user, plan.cefr_sub, "approved", salt
        )
        activity_id = db.scalar(
            insert(Activity)
            .values(
                user_id=user.id,
                session_id=session_id,
                content_id=content_id,
                origin="template" if final.origin == "template" else origin,
                recommended=recommended,
                position=position,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "content_id"])
            .returning(Activity.id)
        )
        if activity_id is not None:
            activity_ids.append(activity_id)
    db.flush()
    return activity_ids
