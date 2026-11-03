"""Geliştirme için TASLAK içerik. Gerçek öğe havuzu ve açıklamalar Işıl'dan gelecek.

Hata etiketleri blueprint'in başlangıç kümesidir; Türkçe açıklamalar onaylanmamıştır.
Öğeler `pool_version = 'dev-seed'` ile işaretlenir; gerçek havuz gelince pasifleştirilir.
"""

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

# (tür, İngilizce, Türkçe, çekimli biçimler)
ITEMS = [
    ("chunk", "work as", "olarak çalışmak", ["works as", "worked as", "working as"]),
    ("word", "live", "yaşamak", ["lives", "lived", "living"]),
    ("word", "like", "sevmek, hoşlanmak", ["likes", "liked", "liking"]),
    ("chunk", "every day", "her gün", []),
    ("word", "breakfast", "kahvaltı", ["breakfasts"]),
    ("chunk", "on Monday", "pazartesi günü", ["on Mondays"]),
    ("word", "weekend", "hafta sonu", ["weekends"]),
    ("chunk", "go to work", "işe gitmek", ["goes to work", "went to work", "going to work"]),
    ("word", "favourite", "en sevdiği", ["favorite"]),
    ("chunk", "there is", "var (tekil)", ["there's"]),
]
# Seviye sözlüğü artık CEFR-J'den gelir: scripts/import_cefrj.py
