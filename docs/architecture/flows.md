# Uygulama akışları

## Ekranlar

`/login`, `/auth/verify`, `/onboarding/consent`, `/onboarding/goals`, `/onboarding/placement`, `/panel`, `/session`, `/practice/recall`, `/practice/reading`, `/practice/writing`, `/practice/dialogue`, `/feedback`, `/curriculum`, `/report`, `/review`.

Yönlendirme onam → hedef → yerleştirme → panel sırasını zorlar. İnceleyen girişten doğrudan `/review`'a gider. Tipler FastAPI şemasından üretilir: `npm run gen:api`.

## Yerleştirme testi

- **Sorular:** `scripts/placement_v1.py`, taslak; 24 özgün soru, A1 ve A2'den 12'şer: kelime, yapı, iki kısa okuma. Dinleme yok. Işıl onayı `import_placement` ile kaydedilir; içerik değişirse yeni sürüm açılır, eski cevaplar eski sürüme bağlı kalır.
- **Puanlama (`onboarding/placement.py`):** A1 %50'nin altındaysa pre-A1; değilse A2 %50'nin altındaysa A1; değilse A2. Alt seviye: kendi seviyesinde en az %80 ise 2, değilse 1. "Bilmiyorum" yanlış sayılır. pre-A1 öğrenci A1.1'den başlar.
- **Akış (`onboarding/fixed_tests.py`):** her cevap `fixed_test_answer`, sonuç `fixed_test_completed` olayı. Doğru cevap gösterilmez, cevaplar tekrar motorunu etkilemez, yarıda kalan test kaldığı yerden sürer. Şıklar kullanıcıya özgü ama sabit sırayla karıştırılır.
- **Etkisi:** A1 öğrencisine yalnızca A1 öğeleri, A2 öğrencisine önce A2 öğeleri gelir; paylaşılan içerik alt seviyeye göre eşleşir.

## Müfredat

`app/curriculum/`.

- **Öneri:** Sonnet, öğrenci özeti, haftalık kapasite ve tüm öğe havuzunu alır; 8 haftalık plan döner: haftalık odak, öğeler, 1–3 Türkçe "yapabilirim" maddesi, beceri ağırlıkları, kısa özet.
- **Kural katmanı (`rules.py`):** tam 8 hafta; yalnızca havuzdaki öğeler; her öğe bir kez; hafta başına en fazla kapasite; havuz ile 8 haftalık kapasiteden küçük olanının en az %80'i planlanmış; odak ve "yapabilirim" dolu. Küçük kusurlar düzeltilir. Ret sebepleri ajana verilip bir kez daha sorulur; geçmezse deterministik yedek plan kaydedilir. Öğrenci her durumda plan görür.
- **Kayıt:** her plan yeni sürüm; kaynak (agent, fallback), özet ve genel ağırlıklar plan satırında.
- **Etkisi:** oturum yeni öğeleri müfredat sırasıyla alır: bu haftanın öğeleri, sonra sonraki haftalar, en son geride kalanlar. Serbest yazma da aynı sırayı izler.
- **Ekran:** `/curriculum`; şu anki hafta işaretli, süre "tahmin" olarak gösterilir. Plan haftaları sürüme görelidir: her yeniden plan yeni bir 8 hafta üretir ve 1. haftası "bu hafta"dır. Gösterilen numara sürüm kadar kaydırılır, öğrencinin sayacı sıfırlanmaz.

## Etkinlik üretimi

`app/sessions/`.

- **Akış (`generation.py`):** tekrar motoru öğeleri seçer → kısa türlerde başkası için üretilmiş onaylı içerik yeniden kullanılır → kalanlar için tek Haiku çağrısı → her etkinlik ayrı doğrulanır (`validation.py`) → kalanlar için bir çağrı daha → yine kalırsa LLM'siz şablon (`templates.py`; okuma için şablon yok, oturumdan çıkar). Reddedilen çıktı `status = rejected` ile saklanır.
- **Türler:** yeni öğe (anlam, 2 örnek, kontrol sorusu), hatırlama (3 şıklı boşluk doldurma ve Türkçe ipucu), mikro okuma (50–80 kelime, 2 soru), yazma görevi. Dinleme henüz yok.
- **Değerlendirme (`service.py`):** cevap sunucuda değerlendirilir; öğrenciye giden görünümde cevap yoktur. Aynı soru iki kez sayılmaz. Tüm etkinlikler bitince `session_completed`.
- **Üretim anı:** gece üretimi gelmediyse `GET /api/session/today` isteği aynı yolu çalıştırır. Bu istek uzun sürebilir: [jobs.md](jobs.md).

## Yazma geri bildirimi

`app/feedback/service.py`.

`give_feedback` metni `writing_submitted` olayı olarak yazar → günün öğrenci özetiyle Sonnet'e sorar → doğrulayıcıdan geçirir → `feedbacks` ve `error_marks` kaydeder. Geçerse birincil hedef öğe için `writing_assessed` yazılır ve tekrar motoru güncellenir. Geçmezse (limit, API hatası, ret, doğrulayıcı) öğrenci "şimdilik atladık" görür, öğrenci modeli değişmez.

Doğru cümle yalnızca `submit_rewrite` ile, yeniden yazmadan sonra döner. Yeniden yazma değerlendirilmiyor, boş olmayan her metin doğruyu açıyor (DZ-9).

**Bekleyen geri bildirim.** Gösterilemeyen yazılar saatlik işle yeniden değerlendirilir ([jobs.md](jobs.md)). Görev metni saklanmaz: etkinlikten ya da serbest pratik şablonundan yeniden kurulur. Hazır olanlar `GET /api/feedback/ready` ile gelir; panelde kart, `/feedback` sayfasında aynı akış. Görülünce `feedback_shown` yazılır ve liste bir daha göstermez.

## Ek çalışma

`app/sessions/extra.py`.

- **Türler:** Tekrar ve Okuma talep anında üretilir; Yazma şablon görevle; Yazılı diyalog aşağıda. Dinleme panelde "yakında".
- **Öğeler kural katmanından:** önce vadesi gelen tekrarlar, sonra en zorlanılanlar. Hiç öğe görülmemişse ek çalışma açılmaz.
- **Aynı hat:** `build_activities`. Etkinlikler `origin = extra`, oturuma bağlı değil.
- **Önerilen (H7):** müfredatın bu haftaki beceri ağırlığı ile gerçekten ayrılan süre arasındaki en büyük açık. Her seçimde `extra_activity_chosen`.

## Yazılı diyalog

`app/dialogue/`.

- **Kural katmanı seçer:** senaryo hedefe göre (`scenarios.py`; amaç başına 3 durum, önceki diyalog sayısıyla döner), hedef öğeler ek çalışmayla aynı yerden, en fazla 2. Senaryo ve açılış cümleleri sabit (taslak, Işıl onayı bekliyor): diyalog LLM'siz başlar.
- **Tur başına tek Sonnet çağrısı:** son cümleye yazma şemasıyla değerlendirme, partnerin sıradaki cümlesi, `done`.
- **Doğrulama:** geri bildirim `validate_feedback`ten geçer; geçemezse gösterilmez ve ertelenmez. Partner cümlesi seviye kontrolünden geçer (izinli isimler, hedef öğeler ve öğrencinin kendi kelimeleri serbest; 1–20 kelime). Geçemezse bir kez daha istenir, sonra sabit cümle.
- **Tur sınırları:** en az 4, en fazla 6 öğrenci cümlesi. Biten diyaloğa cevap 409.
- **Kayıt:** öğrencinin cümlesi `writing_submitted`, partnerin cevabı `dialogue_replied`. Geçmiş yalnızca olaylardan kurulur. Diyalog cümleleri FSRS derecesi üretmez; hata işaretleri haftalık rapordaki en sık hataya girer.
- **Ekran:** sohbet balonları, her cümlenin altında kısa geri bildirim. Doğru cümle gösterilmez (EK-11).

## Haftalık rapor ve yeniden plan

`app/reports/`.

- **Metrikler (`service.py`):** yerel pazartesi–pazar penceresinde yalnızca olaylardan: aktif gün, tamamlanan oturum, yeni öğe, kalıcılaşan öğe (Review durumunda, kararlılık en az 7 gün), tekrar başarısı (Hard ve üstü oranı), beceri başına dakika, "anladım" oranı, ek çalışma seçimi, en sık hata. Rapor bir kez yazılır.
- **Tempo:** başarı %60'ın altındaysa yavaş (kapasite × 0,75), en az %90 ve en az 4 oturumsa hızlı (× 1,25), az veride normal. Şıklı ve yazılı soruları ayırmıyor (DZ-5).
- **Yeniden plan (`weekly.py`):** hafta aktifse ajan ilerleme özetiyle çalışır: derecelendirilmiş olayı olan öğeler havuzdan çıkar, kapasite tempoya göre ayarlanır, `summary_tr` değişikliği ve nedenini söyler. Hiç gelmeyene LLM çağrısı yapılmaz; rapor yine yazılır.
- **Ekran:** `/report`; panelde rapor varsa bağlantı.

## İnceleme

`app/review/`: önce "sorun var" bildirimleri, sonra rastgele örnek. Kaynak sunucuda belirlenir. "Yanlış öğretiyor" kararı içeriği `retired` yapar: yeni öğrencilere gitmez. Tanımlar: [inceleme yönergesi](../content/inceleme-yonergesi.md).

"Sorun var" düğmesi tüm etkinliklerde ve diyalogda var; neden sabit listeden seçilir. Geri bildirim varsa hedef odur.
