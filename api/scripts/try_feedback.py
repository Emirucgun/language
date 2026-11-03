"""Gerçek Claude API ile geri bildirim akışı denemesi (küçük set, ~10 Sonnet çağrısı).

Test veritabanında tek bir transaction içinde çalışır ve sonunda geri alınır: hiçbir
şey kalıcı yazılmaz. Hata etiketleri blueprint'in başlangıç kümesidir; açıklamalar
taslaktır. Seviye sözlüğü henüz boş olduğu için deneme kendi küçük sözlüğünü kullanır.

    cd api
    uv run python -m scripts.try_feedback
"""

import os
import sys
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

load_dotenv()

import app.models  # noqa: E402, F401 - tüm tabloları kaydeder
from app.config import settings  # noqa: E402
from app.feedback.models import Feedback  # noqa: E402
from app.feedback.service import give_feedback  # noqa: E402
from app.llm.client import AnthropicClient  # noqa: E402
from app.llm.models import LlmCall  # noqa: E402
from app.validator.core import Lexicon, words  # noqa: E402

ERROR_TAGS = [
    ("ARTICLE", "Artikel eksik ya da fazla", "Tekil sayılabilen isimden önce a/an gelir."),
    ("SUBJECT", "Özne eksik", "İngilizcede cümlenin öznesi düşmez: It is, She is."),
    ("BE_VERB", "Be fiili eksik ya da yanlış", "İsim cümlelerinde am/is/are gerekir."),
    ("WORD_ORDER", "Kelime sırası", "İngilizcede sıra genelde özne + fiil + nesnedir."),
    ("PREPOSITION", "Edat seçimi", "Gün için on, saat için at, şehir için in kullanılır."),
    ("PLURAL", "Çoğul / sayılabilirlik", "Birden fazla sayılabilen isim -s alır."),
    ("TENSE", "Zaman ya da üçüncü tekil -s", "He/she/it ile geniş zamanda fiil -s alır."),
    ("OTHER", "Diğer", "Bu hata kataloğun dışında."),
]

# (görev, hedef öğe, öğrencinin cümlesi)
SAMPLES = [
    ("Write a sentence about your job.", "work as", "I work as teacher."),
    ("Say what your sister does.", "teacher", "She teacher."),
    ("Describe the weather today.", "nice", "Is very nice."),
    ("Say what you have.", "have", "I have car."),
    ("Describe your city.", "very", "My city is very big."),
    ("Say what your father likes.", "like", "He like coffee."),
    ("Say when you go to school.", "on Monday", "I go in school at Monday."),
    ("Say where you live.", "live in", "I live in Istanbul."),
    ("Say what you did yesterday.", "yesterday", "Yesterday I go to work."),
    ("Say what you eat for breakfast.", "eat", "I am eat bread and cheese."),
]

BASE_WORDS = (
    "i you he she it we they my your his her a an the is am are was were be do does did "
    "go goes went to in on at every day work works as teacher sister city very big small "
    "nice weather today have has car like likes coffee school monday live lives yesterday "
    "eat eats ate bread cheese breakfast and father mother"
)


def main() -> int:
    key = settings.anthropic_api_key
    if key is None or not key.get_secret_value():
        print("ANTHROPIC_API_KEY api/.env içinde tanımlı değil.")
        return 1

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    client = AnthropicClient(api_key=key.get_secret_value())
    sample_words = {w for _, item, sentence in SAMPLES for w in words(item + " " + sentence)}
    lexicon = Lexicon(frozenset(BASE_WORDS.split()) | sample_words)

    with Session(engine) as session:
        for code, name, explanation in ERROR_TAGS:
            session.execute(
                text(
                    "INSERT INTO content.error_tags (code, name_tr, explanation_tr) "
                    "VALUES (:c, :n, :e) ON CONFLICT (code) DO UPDATE "
                    "SET name_tr = :n, explanation_tr = :e, active = true"
                ),
                {"c": code, "n": name, "e": explanation},
            )
        session.execute(
            text("UPDATE content.error_tags SET active = (code = ANY(:codes))"),
            {"codes": [c for c, _, _ in ERROR_TAGS]},
        )
        user_id = session.execute(
            text(
                "INSERT INTO learning.users (email, goal, daily_minutes, interests) "
                "VALUES (:e, 'travel', 15, '{food,football}') RETURNING id"
            ),
            {"e": f"{uuid.uuid4()}@trial.example"},
        ).scalar_one()

        total_cost = 0
        for task, item_text, sentence in SAMPLES:
            item_id = session.execute(
                text(
                    "INSERT INTO content.items (pool_version, kind, text_en, text_tr, cefr) "
                    "VALUES ('trial', 'word', :t, '-', 'A1') RETURNING id"
                ),
                {"t": item_text},
            ).scalar_one()
            view = give_feedback(
                session,
                client,
                user_id=user_id,
                task=task,
                target_item_ids=[item_id],
                learner_text=sentence,
                lexicon=lexicon,
            )
            call = session.scalars(
                select(LlmCall).where(LlmCall.user_id == user_id).order_by(LlmCall.id.desc())
            ).first()
            feedback = session.get(Feedback, view.feedback_id) if view.feedback_id else None
            print(f"\n=== {sentence!r}")
            print(f"  durum: {view.status}  doğru mu: {view.is_correct}")
            if feedback is not None:
                issues = feedback.validator_result.get("issues", [])
                if issues:
                    print(f"  doğrulayıcı: {issues}")
                session.flush()
            if view.status == "shown":
                marks = [(e.code, sentence[e.start : e.end] or "^") for e in view.errors]
                print(f"  hatalar: {marks}")
                print(f"  ipucu: {view.hint_tr}")
                print(f"  düzeltme: {feedback.correction if feedback else None}")
            if call is not None:
                total_cost += call.cost_microusd or 0
                print(
                    f"  token: girdi {call.input_tokens}, önbellek okuma {call.cache_read_tokens}, "
                    f"önbellek yazma {call.cache_write_tokens}, çıktı {call.output_tokens}, "
                    f"{call.latency_ms} ms, ${(call.cost_microusd or 0) / 1e6:.4f}, "
                    f"durum {call.status}/{call.stop_reason}"
                )

        print(f"\nToplam maliyet: ${total_cost / 1e6:.4f}")
        session.rollback()  # deneme hiçbir şey bırakmaz
    engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
