"""Diyalog senaryoları: kural katmanı seçer (hedefe göre), LLM yalnızca konuşmayı sürdürür.

Açılış cümlesi sabittir (taslak, Işıl onayı bekliyor): diyalog LLM'siz başlar, ilk çağrı
öğrencinin ilk cevabıyla yapılır. Aynı senaryo üst üste gelmesin diye kullanıcının önceki
diyalog sayısıyla döndürülür.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scenario:
    key: str
    situation_en: str  # modele giden tarif
    learner_role_en: str
    partner_role_en: str
    scenario_tr: str  # öğrenciye gösterilen
    learner_role_tr: str
    partner_role_tr: str
    opening_en: str
    opening_tr: str


BY_GOAL: dict[str, list[Scenario]] = {
    "travel": [
        Scenario(
            "hotel", "checking in at a small hotel", "guest", "receptionist",
            "Küçük bir otele giriş yapıyorsun.", "Otel misafiri", "Resepsiyon görevlisi",
            "Good evening! Welcome to our hotel. Do you have a room for tonight?",
            "İyi akşamlar! Otelimize hoş geldiniz. Bu gece için odanız var mı?",
        ),
        Scenario(
            "cafe", "ordering breakfast at a café", "customer", "waiter",
            "Bir kafede kahvaltı sipariş ediyorsun.", "Müşteri", "Garson",
            "Good morning! What would you like for breakfast?",
            "Günaydın! Kahvaltıda ne istersiniz?",
        ),
        Scenario(
            "directions", "asking for directions in a new city", "tourist", "local person",
            "Yeni bir şehirde yol soruyorsun.", "Turist", "Şehirde yaşayan biri",
            "Hello! You look lost. Can I help you?",
            "Merhaba! Kaybolmuş gibisin. Yardım edebilir miyim?",
        ),
    ],
    "work": [
        Scenario(
            "new_colleague", "meeting a new colleague at work", "employee", "new colleague",
            "İş yerinde yeni bir çalışma arkadaşıyla tanışıyorsun.", "Çalışan",
            "Yeni iş arkadaşı",
            "Hi! I'm Anna. I'm new here. What do you do in this company?",
            "Merhaba! Ben Anna. Burada yeniyim. Bu şirkette ne iş yapıyorsun?",
        ),
        Scenario(
            "meeting_time", "arranging a meeting time", "employee", "colleague",
            "Bir iş arkadaşınla toplantı saati ayarlıyorsun.", "Çalışan", "İş arkadaşı",
            "Hi! We need a meeting this week. When are you free?",
            "Merhaba! Bu hafta bir toplantı yapmamız gerek. Ne zaman boşsun?",
        ),
        Scenario(
            "lunch", "talking about lunch plans with a colleague", "employee", "colleague",
            "Bir iş arkadaşınla öğle yemeği planı yapıyorsun.", "Çalışan", "İş arkadaşı",
            "It's almost twelve. Do you want to have lunch together?",
            "Saat neredeyse on iki. Birlikte öğle yemeği yemek ister misin?",
        ),
    ],
    "school": [
        Scenario(
            "classmate", "meeting a classmate on the first day", "student", "classmate",
            "Okulun ilk gününde bir sınıf arkadaşınla tanışıyorsun.", "Öğrenci",
            "Sınıf arkadaşı",
            "Hi! Is this your first day too? Where are you from?",
            "Merhaba! Senin de ilk günün mü? Nerelisin?",
        ),
        Scenario(
            "homework", "asking a classmate about homework", "student", "classmate",
            "Bir sınıf arkadaşına ödevi soruyorsun.", "Öğrenci", "Sınıf arkadaşı",
            "Hi! Did you finish the homework for tomorrow?",
            "Merhaba! Yarınki ödevi bitirdin mi?",
        ),
        Scenario(
            "library", "asking for a book at the library", "student", "librarian",
            "Kütüphanede bir kitap arıyorsun.", "Öğrenci", "Kütüphane görevlisi",
            "Hello! Can I help you find a book?",
            "Merhaba! Kitap bulmanıza yardım edebilir miyim?",
        ),
    ],
    "daily_conversation": [
        Scenario(
            "weekend", "talking about the weekend with a friend", "friend", "friend",
            "Bir arkadaşınla hafta sonunu konuşuyorsun.", "Arkadaş", "Arkadaşın",
            "Hi! How was your weekend? What did you do?",
            "Selam! Hafta sonun nasıldı? Ne yaptın?",
        ),
        Scenario(
            "shopping", "buying clothes in a shop", "customer", "shop assistant",
            "Bir mağazada kıyafet alıyorsun.", "Müşteri", "Mağaza çalışanı",
            "Hello! Are you looking for something today?",
            "Merhaba! Bugün bir şey mi arıyorsunuz?",
        ),
        Scenario(
            "neighbour", "meeting a new neighbour", "neighbour", "new neighbour",
            "Yeni komşunla tanışıyorsun.", "Komşu", "Yeni komşun",
            "Hello! I'm Tom. I live next door now. Do you live here too?",
            "Merhaba! Ben Tom. Artık yan dairede oturuyorum. Sen de burada mı yaşıyorsun?",
        ),
    ],
}

SCENARIOS: dict[str, Scenario] = {s.key: s for group in BY_GOAL.values() for s in group}


def pick(goal: str | None, previous_dialogues: int) -> Scenario:
    options = BY_GOAL.get(goal or "", BY_GOAL["daily_conversation"])
    return options[previous_dialogues % len(options)]
