"""Seviye testi B formu, sürüm 1: TASLAK (özgün sorular; Işıl onayı bekliyor).

A formuyla paralel: aynı bölüm ve seviye dağılımı, aynı yapılar, başka kelime ve metinler.
Öğrencilerin yarısı A ile başlayıp B ile bitirir, yarısı tersi. Bu yüzden formların zorluğu
yakın olmalı; fark varsa çapraz atama sonucu dengeler ama analizde ayrıca görünür.
"""

A1_TEXT = (
    "My name is Can. I am 30 years old and I live in Bursa with my parents. "
    "I am a cook. I work at a restaurant in the city centre. I usually go to work by car. "
    "On Saturdays I don't work. I play football with my friends and we drink tea in the park."
)

A2_TEXT = (
    "Last winter Zeynep went to Rome for the first time. She stayed with her aunt, who teaches "
    "at a language school there. The streets were more crowded than she expected, so she "
    "walked early in the morning. She wanted to visit a famous palace, but it was closed for "
    "repairs. Instead, she joined a cooking class and visited a small market. "
    "She is planning to return in spring with her brother."
)


def _q(
    identity: str,
    section: str,
    level: str,
    prompt: str,
    options: list[str],
    passage: str | None = None,
) -> dict[str, object]:
    """İlk şık doğru cevaptır; öğrenciye karıştırılarak gider."""
    question: dict[str, object] = {
        "id": identity,
        "section": section,
        "level": level,
        "prompt": prompt,
        "options": options,
        "answer": options[0],
    }
    if passage:
        question["passage"] = passage
    return question


QUESTIONS: list[dict[str, object]] = [
    # --- A1: kelime ---
    _q("bv1", "vocabulary", "A1", "“masa” in English:", ["table", "window", "shoe", "cup"]),
    _q(
        "bv2",
        "vocabulary",
        "A1",
        "Which one is a month?",
        ["June", "Friday", "Winter", "Evening"],
    ),
    _q(
        "bv3",
        "vocabulary",
        "A1",
        "My father's sister is my ___.",
        ["aunt", "niece", "daughter", "uncle"],
    ),
    # --- A1: yapı ---
    _q("bg1", "grammar", "A1", "They ___ students.", ["are", "is", "am", "be"]),
    _q("bg2", "grammar", "A1", "She has ___ apple.", ["an", "a", "–", "the an"]),
    _q(
        "bg3",
        "grammar",
        "A1",
        "My sister ___ in a bank.",
        ["works", "work", "working", "is work"],
    ),
    _q("bg4", "grammar", "A1", "The meeting is ___ Monday.", ["on", "in", "at", "to"]),
    _q("bg5", "grammar", "A1", "___ your brother live here?", ["Does", "Do", "Is", "Are"]),
    _q("bg6", "grammar", "A1", "There ___ a cat under the chair.", ["is", "are", "be", "has"]),
    # --- A1: okuma ---
    _q(
        "br1",
        "reading",
        "A1",
        "What is Can's job?",
        ["He is a cook.", "He is a doctor.", "He is a driver."],
        A1_TEXT,
    ),
    _q(
        "br2",
        "reading",
        "A1",
        "Who does Can live with?",
        ["With his parents.", "With his wife.", "With his friends."],
        A1_TEXT,
    ),
    _q(
        "br3",
        "reading",
        "A1",
        "What does Can do on Saturdays?",
        ["He plays football.", "He works at the restaurant.", "He visits his uncle."],
        A1_TEXT,
    ),
    # --- A2: kelime ---
    _q(
        "bv4",
        "vocabulary",
        "A2",
        "I can't carry this bag. It's too ___.",
        ["heavy", "quiet", "early", "thin"],
    ),
    _q(
        "bv5",
        "vocabulary",
        "A2",
        "You need a ___ to get on the train.",
        ["ticket", "blanket", "mirror", "stamp"],
    ),
    _q(
        "bv6",
        "vocabulary",
        "A2",
        "The opposite of “remember” is:",
        ["forget", "decide", "repeat", "explain"],
    ),
    # --- A2: yapı ---
    _q(
        "bg7",
        "grammar",
        "A2",
        "She ___ a new phone yesterday.",
        ["bought", "buy", "has bought", "was buy"],
    ),
    _q(
        "bg8",
        "grammar",
        "A2",
        "This exercise is ___ than the first one.",
        ["easier", "more easy", "easiest", "easy"],
    ),
    _q(
        "bg9",
        "grammar",
        "A2",
        "Be quiet! The baby ___.",
        ["is sleeping", "sleeps", "sleep", "slept"],
    ),
    _q(
        "bg10",
        "grammar",
        "A2",
        "I ___ start a new job next month.",
        ["am going to", "going to", "go to", "will to"],
    ),
    _q("bg11", "grammar", "A2", "Have you ever ___ to Paris?", ["been", "was", "be", "being"]),
    _q(
        "bg12",
        "grammar",
        "A2",
        "You ___ smoke in the hospital. It's not allowed.",
        ["mustn't", "can", "should", "would"],
    ),
    # --- A2: okuma ---
    _q(
        "br4",
        "reading",
        "A2",
        "Why did Zeynep walk early in the morning?",
        ["The streets were crowded.", "Her aunt asked her to.", "She had a class."],
        A2_TEXT,
    ),
    _q(
        "br5",
        "reading",
        "A2",
        "Why didn't Zeynep visit the palace?",
        ["It was closed.", "The tickets were expensive.", "Her aunt was busy."],
        A2_TEXT,
    ),
    _q(
        "br6",
        "reading",
        "A2",
        "What is Zeynep's plan?",
        ["To return with her brother.", "To teach at a school.", "To live in Rome."],
        A2_TEXT,
    ),
]
