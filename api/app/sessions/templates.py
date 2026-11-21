"""LLM'siz yedek etkinlikler: üretim ya da doğrulama başarısız olursa oturum yine dolar.

Şablonlar sade ama her zaman doğrudur: içerik yalnızca küratörlü öğe alanlarından gelir.
"""

import random
from collections.abc import Sequence

from app.sessions.schemas import OPTION_COUNT, Choice, Recall, Writing
from app.sessions.validation import ItemCard


def recall_from_card(card: ItemCard, distractors: Sequence[ItemCard]) -> Recall | None:
    """Türkçe → İngilizce seçmeli soru: "“her gün” in English: ___".

    Çeldirici havuzdan rastgele ama öğeye göre sabit seçilir. Yeterli çeldirici yoksa soru
    üretilmez: az şıklı soru tahminle kolaylaşır.
    """
    candidates = sorted({d.text_en for d in distractors if d.id != card.id} - {card.text_en})
    if len(candidates) < OPTION_COUNT - 1:
        return None
    others = random.Random(card.id).sample(candidates, OPTION_COUNT - 1)
    options = sorted([card.text_en, *others], key=str.lower)
    return Recall(
        item_id=card.id,
        question=Choice(
            prompt=f"“{card.text_tr}” in English: ___",
            options=options,
            answer=card.text_en,
        ),
        # Soru zaten Türkçeyi gösteriyor; ipucu tekrar olurdu ve dereceyi boşuna düşürürdü.
        hint_tr="",
    )


def writing_from_card(card: ItemCard) -> Writing:
    return Writing(
        item_id=card.id,
        task_en=f'Write one sentence about yourself using "{card.text_en}".',
        task_tr=f"“{card.text_en}” ({card.text_tr}) kullanarak kendinle ilgili bir cümle yaz.",
    )
