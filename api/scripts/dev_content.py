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

# Küçük A1 temel kelime listesi (yalnızca geliştirme; gerçek liste açık karar).
A1_WORDS = """
a an the i you he she it we they me him her us them my your his its our their this that
these those is am are was were be been do does did have has had can will not no yes and
or but because so very too also only all some any many much more most one two three four
five first last next new old good bad big small long short hot cold nice happy sad easy
hard here there where when what who how why which now today tomorrow yesterday always
usually often sometimes never morning afternoon evening night day week month year time
monday tuesday wednesday thursday friday saturday sunday at in on to from with for of
about after before by up down out go goes went come comes came get gets got make makes
made take takes took see sees saw know knows knew think thinks want wants like likes love
loves live lives work works play plays read reads write writes eat eats ate drink drinks
cook cooks watch watches listen listens speak speaks talk talks walk walks run runs drive
drives buy buys pay pays study studies learn learns teach teaches help helps open close
start finish stay visit visits travel travels sleep sleeps wake wakes
home house room kitchen school work office shop market city town country street car bus
train plane bike family mother father brother sister friend son daughter wife husband
child children man woman people teacher student doctor driver job name food water coffee
tea milk bread cheese egg eggs fruit apple breakfast lunch dinner book phone money music
film football game sport weather sun rain holiday weekend
"""
