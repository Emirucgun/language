"""Yerleştirme testi v1 — TASLAK (özgün sorular; Işıl onayı bekliyor).

24 soru: kelime + yapı + iki kısa okuma; A1 ve A2 eşit ağırlıkta. Dinleme bölümü TTS
sağlayıcısı seçilince eklenecek (sürüm 2). Türkçe konuşanların tipik hataları bilerek
çeldirici olarak kullanıldı (artikel, be fiili, üçüncü tekil -s, edat).
"""

A1_TEXT = (
    "My name is Elif. I am 25 years old and I live in Izmir with my sister. "
    "I am a nurse. I work at a hospital near our flat. I usually go to work by bus. "
    "On Sundays I don't work. I meet my friends and we have breakfast by the sea."
)

A2_TEXT = (
    "Last summer Mehmet visited London for the first time. He stayed with his cousin, who "
    "works in a hotel there. The weather was cooler than in Ankara, so he bought a jacket on "
    "the second day. He wanted to see a football match, but the tickets were too expensive. "
    "Instead, he went to a free museum and took a boat trip on the river. "
    "He is planning to go back next year with his wife."
)

QUESTIONS: list[dict[str, object]] = [
    # --- A1: kelime ---
    {
        "id": "v1",
        "section": "vocabulary",
        "level": "A1",
        "prompt": "“kitap” in English:",
        "options": ["book", "door", "bag", "pen"],
        "answer": "book",
    },
    {
        "id": "v2",
        "section": "vocabulary",
        "level": "A1",
        "prompt": "Which one is a day of the week?",
        "options": ["March", "Tuesday", "Summer", "Morning"],
        "answer": "Tuesday",
    },
    {
        "id": "v3",
        "section": "vocabulary",
        "level": "A1",
        "prompt": "My mother's brother is my ___.",
        "options": ["uncle", "cousin", "son", "aunt"],
        "answer": "uncle",
    },
    # --- A1: yapı ---
    {
        "id": "g1",
        "section": "grammar",
        "level": "A1",
        "prompt": "She ___ a teacher.",
        "options": ["is", "are", "am", "be"],
        "answer": "is",
    },
    {
        "id": "g2",
        "section": "grammar",
        "level": "A1",
        "prompt": "I have ___ car.",
        "options": ["a", "an", "–", "the a"],
        "answer": "a",
    },
    {
        "id": "g3",
        "section": "grammar",
        "level": "A1",
        "prompt": "He ___ coffee every morning.",
        "options": ["drink", "drinks", "drinking", "is drink"],
        "answer": "drinks",
    },
    {
        "id": "g4",
        "section": "grammar",
        "level": "A1",
        "prompt": "My birthday is ___ May.",
        "options": ["in", "on", "at", "to"],
        "answer": "in",
    },
    {
        "id": "g5",
        "section": "grammar",
        "level": "A1",
        "prompt": "___ you like tea?",
        "options": ["Do", "Does", "Are", "Is"],
        "answer": "Do",
    },
    {
        "id": "g6",
        "section": "grammar",
        "level": "A1",
        "prompt": "There ___ two books on the table.",
        "options": ["are", "is", "be", "has"],
        "answer": "are",
    },
    # --- A1: okuma ---
    {
        "id": "r1",
        "section": "reading",
        "level": "A1",
        "passage": A1_TEXT,
        "prompt": "What is Elif's job?",
        "options": ["She is a nurse.", "She is a teacher.", "She is a driver."],
        "answer": "She is a nurse.",
    },
    {
        "id": "r2",
        "section": "reading",
        "level": "A1",
        "passage": A1_TEXT,
        "prompt": "How does Elif usually go to work?",
        "options": ["By bus.", "By car.", "On foot."],
        "answer": "By bus.",
    },
    {
        "id": "r3",
        "section": "reading",
        "level": "A1",
        "passage": A1_TEXT,
        "prompt": "What does Elif do on Sundays?",
        "options": [
            "She works at the hospital.",
            "She meets her friends.",
            "She visits her mother.",
        ],
        "answer": "She meets her friends.",
    },
    # --- A2: kelime ---
    {
        "id": "v4",
        "section": "vocabulary",
        "level": "A2",
        "prompt": "I can't buy it. It's too ___.",
        "options": ["expensive", "cheap", "early", "careful"],
        "answer": "expensive",
    },
    {
        "id": "v5",
        "section": "vocabulary",
        "level": "A2",
        "prompt": "You need a ___ to travel to another country.",
        "options": ["passport", "receipt", "wallet", "pillow"],
        "answer": "passport",
    },
    {
        "id": "v6",
        "section": "vocabulary",
        "level": "A2",
        "prompt": "The opposite of “borrow” is:",
        "options": ["lend", "keep", "spend", "send"],
        "answer": "lend",
    },
    # --- A2: yapı ---
    {
        "id": "g7",
        "section": "grammar",
        "level": "A2",
        "prompt": "I ___ to Antalya last year.",
        "options": ["went", "go", "have gone", "was go"],
        "answer": "went",
    },
    {
        "id": "g8",
        "section": "grammar",
        "level": "A2",
        "prompt": "Istanbul is ___ than Ankara.",
        "options": ["bigger", "more big", "biggest", "big"],
        "answer": "bigger",
    },
    {
        "id": "g9",
        "section": "grammar",
        "level": "A2",
        "prompt": "Look! It ___ outside.",
        "options": ["is raining", "rains", "rain", "rained"],
        "answer": "is raining",
    },
    {
        "id": "g10",
        "section": "grammar",
        "level": "A2",
        "prompt": "We ___ visit my grandparents next weekend.",
        "options": ["are going to", "going to", "go to", "will to"],
        "answer": "are going to",
    },
    {
        "id": "g11",
        "section": "grammar",
        "level": "A2",
        "prompt": "Have you ever ___ sushi?",
        "options": ["eaten", "ate", "eat", "eating"],
        "answer": "eaten",
    },
    {
        "id": "g12",
        "section": "grammar",
        "level": "A2",
        "prompt": "You ___ wear a seat belt in the car. It's the law.",
        "options": ["must", "can", "may", "would"],
        "answer": "must",
    },
    # --- A2: okuma ---
    {
        "id": "r4",
        "section": "reading",
        "level": "A2",
        "passage": A2_TEXT,
        "prompt": "Why did Mehmet buy a jacket?",
        "options": [
            "It was cooler than in Ankara.",
            "His cousin gave him money.",
            "He lost his old jacket.",
        ],
        "answer": "It was cooler than in Ankara.",
    },
    {
        "id": "r5",
        "section": "reading",
        "level": "A2",
        "passage": A2_TEXT,
        "prompt": "Why didn't Mehmet see a football match?",
        "options": [
            "The tickets cost too much.",
            "There were no matches.",
            "His cousin was working.",
        ],
        "answer": "The tickets cost too much.",
    },
    {
        "id": "r6",
        "section": "reading",
        "level": "A2",
        "passage": A2_TEXT,
        "prompt": "What is Mehmet's plan?",
        "options": ["To go back with his wife.", "To work in a hotel.", "To move to London."],
        "answer": "To go back with his wife.",
    },
]
