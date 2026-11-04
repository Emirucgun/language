"""Yazılı diyalog akışı (docs/architecture/flows.md).

    kural katmanı senaryoyu ve hedef öğeleri seçer → sabit açılış cümlesi (LLM yok)
    → her öğrenci cümlesi: olay → tek Sonnet çağrısı (geri bildirim + partner cümlesi)
    → geri bildirim yazma doğrulayıcısından, partner cümlesi seviye kontrolünden geçer

Konuşma akışı kesilmesin diye: geçemeyen geri bildirim gösterilmez (kaydedilir, ertelenmez;
canlı konuşmada sonradan gelen düzeltmenin anlamı yok), geçemeyen partner cümlesi bir kez
yeniden istenir, yine geçemezse sabit bir cümle kullanılır. Diyalog derecelendirilmez:
cümleler hedef öğeyi sınamak için yazılmıyor. Hata işaretleri haftalık rapora girer.
Commit çağırana aittir.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.models import Item
from app.dialogue.scenarios import SCENARIOS, Scenario, pick
from app.dialogue.schemas import (
    MAX_TURNS,
    MIN_TURNS,
    DialogueTurn,
    DialogueView,
    PartnerLine,
    TurnView,
)
from app.events.models import Event
from app.events.service import record_event
from app.feedback import prompt as feedback_prompt
from app.feedback.models import Feedback
from app.feedback.service import active_tags, store_feedback, stored_view
from app.llm.client import LLMClient
from app.llm.prompts import render_static
from app.llm.service import DailyLimitExceeded, Prompt, generate_structured
from app.llm.snapshot import daily_snapshot
from app.onboarding.fixed_tests import user_level
from app.scheduler.service import lock_user
from app.sessions.extra import NothingToPractise, practice_items, recommend
from app.sessions.models import Activity, ActivityContent
from app.sessions.validation import NAMES, PLACES
from app.validator.activity import check_level, check_word_count
from app.validator.core import VALIDATOR_VERSION, Lexicon, ValidationResult, load_lexicon, words
from app.validator.feedback import validate_feedback

log = structlog.get_logger()

PROMPT_VERSION = "v2"  # v2: hata yeri karakter konumu değil alıntı (konumu sunucu bulur)
TARGET_ITEMS = 2
PARTNER_WORDS = (1, 20)  # prompt 15 diyor; doğrulayıcı biraz pay bırakır
FALLBACK_CONTINUE = PartnerLine(
    en="I see. Can you tell me more?", tr="Anlıyorum. Biraz daha anlatır mısın?"
)
FALLBACK_CLOSE = PartnerLine(
    en="Thank you! It was nice to talk to you.", tr="Teşekkürler! Seninle konuşmak güzeldi."
)


class DialogueNotFound(Exception):
    pass


class DialogueFinished(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Dialogue:
    activity: Activity
    scenario: Scenario
    item_ids: list[int]


# --- Başlatma -----------------------------------------------------------------


def start(db: Session, user: User) -> int:
    """Yeni diyalog etkinliği açar (LLM çağrısı yok); etkinlik id'sini döner."""
    lock_user(db, user.id)
    previous = db.scalar(
        select(func.count())
        .select_from(Activity)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(Activity.user_id == user.id, ActivityContent.kind == "dialogue")
    )
    scenario = pick(user.goal, previous or 0)
    try:
        item_ids = practice_items(db, user, TARGET_ITEMS)
    except NothingToPractise:
        item_ids = []  # henüz öğe görülmemiş: hedefsiz serbest konuşma
    _, cefr_sub = user_level(db, user.id)

    content = {"scenario": scenario.key, "item_ids": item_ids}
    # Diyalog paylaşılmaz: her açılış kullanıcıya özel ayrı içeriktir.
    salt = f"dialogue:{user.id}:{uuid.uuid4()}"
    canonical = json.dumps(content, sort_keys=True)
    content_row = ActivityContent(
        content_hash=hashlib.sha256(f"dialogue|{salt}|{canonical}".encode()).digest(),
        kind="dialogue",
        item_ids=item_ids,
        cefr_sub=cefr_sub,
        interest_tag=None,
        content=content,
        validator_version=VALIDATOR_VERSION,
        validator_result=ValidationResult().to_dict(),
        status="approved",
        shareable=False,
    )
    db.add(content_row)
    db.flush()
    activity = Activity(
        user_id=user.id, content_id=content_row.id, origin="extra", recommended=False
    )
    db.add(activity)
    db.flush()
    record_event(
        db,
        user_id=user.id,
        type="extra_activity_chosen",
        payload={"recommended_kind": recommend(db, user), "chosen_kind": "dialogue"},
        activity_id=activity.id,
    )
    return activity.id


def load(db: Session, user_id: uuid.UUID, activity_id: int) -> Dialogue:
    row = db.execute(
        select(Activity, ActivityContent)
        .join(ActivityContent, ActivityContent.id == Activity.content_id)
        .where(
            Activity.id == activity_id,
            Activity.user_id == user_id,
            ActivityContent.kind == "dialogue",
        )
    ).first()
    if row is None:
        raise DialogueNotFound(activity_id)
    activity, content = row
    return Dialogue(
        activity, SCENARIOS[content.content["scenario"]], list(content.content["item_ids"])
    )


# --- Geçmiş (yalnızca olaylardan) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class Turn:
    learner: str
    reply: dict[str, object]  # dialogue_replied payload'u


def load_turns(db: Session, activity_id: int) -> list[Turn]:
    replies = db.scalars(
        select(Event.payload)
        .where(Event.activity_id == activity_id, Event.type == "dialogue_replied")
        .order_by(Event.id)
    ).all()
    texts: dict[int, str] = {
        event_id: text
        for event_id, text in db.execute(
            select(Event.id, Event.payload["text"].astext).where(
                Event.id.in_([int(r["writing_event_id"]) for r in replies])
            )
        )
    }
    return [Turn(texts[int(r["writing_event_id"])], r) for r in replies]


def _item_texts(db: Session, item_ids: list[int]) -> list[str]:
    items = {i.id: i.text_en for i in db.scalars(select(Item).where(Item.id.in_(item_ids)))}
    return [items[i] for i in item_ids if i in items]


def view(db: Session, dialogue: Dialogue) -> DialogueView:
    turns = load_turns(db, dialogue.activity.id)
    s = dialogue.scenario
    shown: list[TurnView] = []
    for t in turns:
        feedback_id = t.reply["feedback_id"]
        feedback = db.get_one(Feedback, feedback_id) if feedback_id is not None else None
        shown.append(
            TurnView(
                learner=t.learner,
                feedback=stored_view(db, feedback) if feedback else None,
                partner=PartnerLine(en=str(t.reply["partner_en"]), tr=str(t.reply["partner_tr"])),
            )
        )
    return DialogueView(
        activity_id=dialogue.activity.id,
        scenario_tr=s.scenario_tr,
        learner_role_tr=s.learner_role_tr,
        partner_role_tr=s.partner_role_tr,
        target_items=_item_texts(db, dialogue.item_ids),
        opening=PartnerLine(en=s.opening_en, tr=s.opening_tr),
        turns=shown,
        done=bool(turns and turns[-1].reply["done"]),
    )


# --- Bir tur ------------------------------------------------------------------


def _task(
    scenario: Scenario, targets: list[str], history: list[Turn], learner_text: str, turn: int
) -> str:
    lines = [
        f"Situation: {scenario.situation_en}. "
        f"The learner is the {scenario.learner_role_en}; you are the {scenario.partner_role_en}.",
        f"Target item(s): {', '.join(repr(t) for t in targets) or 'none'}",
        "Conversation so far:",
        f"You: {scenario.opening_en}",
    ]
    for t in history:
        lines += [f"Learner: {t.learner}", f"You: {t.reply['partner_en']}"]
    lines.append(f"Learner turn {turn} (the conversation lasts {MIN_TURNS}-{MAX_TURNS} turns).")
    if turn >= MAX_TURNS:
        lines.append("This is the last learner turn: close the conversation and set done to true.")
    elif turn < MIN_TURNS:
        lines.append("It is too early to end: keep the conversation going, done is false.")
    lines.append(f"Learner: {learner_text}")
    return "\n".join(lines)


def validate_partner(
    line: PartnerLine, *, learner_text: str, targets: list[str], lexicon: Lexicon
) -> ValidationResult:
    result = ValidationResult()
    check_word_count(line.en, PARTNER_WORDS, result)
    # Öğrencinin kendi kelimelerini geri kullanmak doğaldır; onlar seviye dışı sayılmaz.
    check_level(line.en, lexicon, result, [*NAMES, *PLACES, *targets, *words(learner_text)])
    if not line.tr.strip():
        result.add("missing_tr", "Türkçe çeviri boş")
    return result


def reply(
    db: Session,
    client: LLMClient,
    dialogue: Dialogue,
    learner_text: str,
    *,
    lexicon: Lexicon | None = None,
) -> TurnView:
    user_id = dialogue.activity.user_id
    lock_user(db, user_id)
    history = load_turns(db, dialogue.activity.id)
    if history and history[-1].reply["done"]:
        raise DialogueFinished(dialogue.activity.id)
    turn = len(history) + 1
    writing = record_event(
        db,
        user_id=user_id,
        type="writing_submitted",
        payload={"text": learner_text, "attempt": 1},
        activity_id=dialogue.activity.id,
    )

    lexicon = lexicon or load_lexicon(db)
    targets = _item_texts(db, dialogue.item_ids)
    snapshot = daily_snapshot(db, user_id)
    prompt = Prompt(
        purpose="dialogue",
        prompt_version=PROMPT_VERSION,
        static_block=render_static(
            "dialogue", PROMPT_VERSION, {"ERROR_CATALOG": feedback_prompt.error_catalog(db)}
        ),
        snapshot_id=snapshot.id,
        snapshot_block=snapshot.text,
        task=_task(dialogue.scenario, targets, history, learner_text, turn),
    )
    codes = set(active_tags(db))

    feedback: Feedback | None = None
    partner: PartnerLine | None = None
    done = False
    for _ in range(2):
        try:
            parsed, call = generate_structured(
                db, client, prompt=prompt, output_type=DialogueTurn, user_id=user_id
            )
        except DailyLimitExceeded:
            break
        if parsed is None:
            continue
        if feedback is None:
            check = validate_feedback(
                parsed.feedback, learner_text=learner_text, catalog_codes=codes, lexicon=lexicon
            )
            feedback = store_feedback(
                db,
                writing_event_id=writing.id,
                llm_call_id=call.id,
                status="shown" if check.ok else "rejected",
                validation=check,
                parsed=parsed.feedback,
            )
        check = validate_partner(
            parsed.partner, learner_text=learner_text, targets=targets, lexicon=lexicon
        )
        if check.ok:
            partner, done = parsed.partner, parsed.done
            break
        log.info("dialogue_partner_rejected", llm_call_id=call.id, **check.to_dict())

    source = "llm" if partner is not None else "fallback"
    if partner is None:
        partner = FALLBACK_CLOSE if turn >= MIN_TURNS else FALLBACK_CONTINUE
        done = turn >= MIN_TURNS
    # Tur sınırları kural katmanında: model erken bitiremez, geç bırakamaz.
    done = turn >= MAX_TURNS or (done and turn >= MIN_TURNS)
    if feedback is not None and feedback.status != "shown":
        feedback = None
    record_event(
        db,
        user_id=user_id,
        type="dialogue_replied",
        payload={
            "turn": turn,
            "writing_event_id": writing.id,
            "feedback_id": feedback.id if feedback else None,
            "partner_en": partner.en,
            "partner_tr": partner.tr,
            "source": source,
            "done": done,
        },
        activity_id=dialogue.activity.id,
    )
    return TurnView(
        learner=learner_text,
        feedback=stored_view(db, feedback) if feedback else None,
        partner=partner,
    )
