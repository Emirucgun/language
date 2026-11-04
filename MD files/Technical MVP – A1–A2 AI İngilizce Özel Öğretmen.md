# Technical MVP – A1–A2 AI İngilizce Özel Öğretmen

Nov 3, 2026 · CTO notu · Kaynak: "MVP Roadmap ve Blueprint" dokümanı

Bu doküman, ürün blueprint'indeki kararları koda dönüştürülebilir teknik kararlara çevirir. Ürün dokümanı **ne** ve **neden**; bu doküman **nasıl** sorusunu cevaplar. Çelişki olursa ürün dokümanının hipotezleri (H1–H7) ve kapsam kuralı geçerlidir; teknik kararlar onlara hizmet eder.

## 1. Stack kararı (CTO onayı)

Blueprint'teki öneri yığını **onaylandı**, aşağıdaki netleştirmeler ve eklemelerle.

| Katman | Karar | Sürüm (3 Kas 2026) | Not |
| --- | --- | --- | --- |
| Arayüz | Next.js (App Router) + TypeScript + Tailwind CSS | next 16.4, react 19.3, tailwindcss 4.3 | Yalnızca arayüz. İş mantığı Next route handler'larında **yazılmaz**. |
| PWA | Serwist (`@serwist/next`) | 9.5 | Manifest + basit önbellek; çevrimdışı mod MVP'de yok |
| API | Python + FastAPI + Pydantic v2 | Python 3.14, fastapi 0.162, pydantic 2.14 | Tekrar motoru, doğrulayıcı ve değerlendirme betikleri tek dilde |
| ORM / göç | SQLAlchemy 2.x + Alembic + psycopg 3 | sqlalchemy 2.1, alembic 1.20, psycopg 3.3 | |
| Veritabanı | PostgreSQL | 18 | Yerelde Windows'a doğrudan kurulum (Docker yok, bkz. Bölüm 9) |
| Arka plan işleri | **procrastinate** (Postgres tabanlı kuyruk + zamanlanmış görev) | 3.10 | **Ekleme.** Redis gerekmez; gece oturum üretimi ve pazar raporu bununla |
| Tekrar motoru | `fsrs` (py-fsrs, açık kaynak FSRS) | 6.3 | Kendi `scheduler` modülümüzün arkasında sarmalanır |
| Kimlik | Kendi magic-link akışımız (FastAPI) + davet kodu | — | Ayrıntı Bölüm 5 |
| LLM | Anthropic Claude API (`anthropic` Python SDK), ince soyutlama (`LLMClient`) arkasında | Claude Sonnet 5.5 + Claude Haiku 5.5 | Karar 3 Kas 2026, bkz. Bölüm 6.1 |
| TTS | Sağlayıcı API'si; ses dosyaları nesne deposunda | — | Yedek: tarayıcı `speechSynthesis` |
| Nesne deposu | S3 uyumlu, AB bölgesi | — | **Ekleme.** TTS çıktıları için |
| E-posta | AB'de işlem yapan transactional e-posta servisi | — | **Ekleme.** Magic link için zorunlu |
| Paket yönetimi | Python: **uv**, Node: **npm** | uv 0.13, Node 26 LTS | uv Python sürümünü de yönetir |
| Kalite araçları | ruff, mypy, pytest; ESLint, Vitest (gerekirse), Playwright (duman testi) | ruff 0.17, mypy 2.4, pytest 9.2 | |
| Loglama | structlog (JSON log) | 26.1 | Hata izleme servisi pilot öncesi değerlendirilir |

**Neden iki dil kabul edildi.** Tek kişilik projede iki dil ek yüktür; ama ürünün çekirdeği (FSRS, öğrenci modeli, doğrulayıcı, altın set betikleri, pilot analizi) Python'da daha doğal ve ileride knowledge tracing'e açıktır. Ek yükü azaltmak için:

- Arayüz yalnızca API'yi çağırır; tipler FastAPI'nin OpenAPI şemasından **otomatik üretilir** (`openapi-typescript`). İki dilde elle tip tanımı tutulmaz.
- Next.js `rewrites` ile `/api/*` isteklerini FastAPI'ye yönlendirir. Tarayıcı tek origin görür: CORS yok, oturum çerezi basit kalır.

**Reddedilen alternatifler.** Docker (makinede 6 GB RAM var; WSL2 + Docker Desktop geliştirmeyi yavaşlatır), Redis/Celery (procrastinate yeterli, bir altyapı parçası eksik), hazır auth servisi (pilot 50 kişi; kendi magic link'imiz ~1 günlük iş ve veriyi tek yerde tutar), tamamen TypeScript (ts-fsrs var ama değerlendirme ve analiz tarafı Python'da kalacaktı).

## 2. Depo yapısı

Tek depo (monorepo), git ile, GitHub'da özel depo.

```
/
├─ web/            Next.js PWA (arayüz)
├─ api/            FastAPI uygulaması + procrastinate worker
│  ├─ app/
│  │  ├─ auth/          magic link, oturum, davet kodu
│  │  ├─ onboarding/    onam, hedef anketi, yerleştirme testi
│  │  ├─ content/       öğe havuzu, hata etiketleri (içe aktarma)
│  │  ├─ curriculum/    müfredat ajanı (LLM) + kural doğrulayıcı
│  │  ├─ scheduler/     FSRS sarmalayıcı, öğe seçimi
│  │  ├─ sessions/      bugünün oturumu, ek çalışma, etkinlik üretimi
│  │  ├─ feedback/      yazma ve diyalog geri bildirimi
│  │  ├─ validator/     deterministik doğrulama kuralları
│  │  ├─ events/        olay kaydı (yalnızca ekleme), yeniden oynatma
│  │  ├─ reports/       haftalık rapor, yeniden planlama tetikleyicisi
│  │  ├─ llm/           LLMClient, sağlayıcı adaptörleri, prompt şablonları
│  │  └─ tts/           TTS adaptörü, nesne deposu
│  ├─ migrations/   Alembic
│  └─ tests/
├─ content/        Işıl'ın öğe havuzu (CSV/YAML), hata etiketleri, sabit testler
├─ eval/           altın set, değerlendirme betikleri, analiz not defterleri (H1–H7)
└─ MD files/       ürün ve teknik dokümanlar, karar kaydı
```

İçerik (`content/`) kodla aynı depoda, sürüm kontrollü durur: hangi öğe havuzu sürümüyle hangi etkinliğin üretildiği izlenebilir. Işıl'ın düzenlediği format basit bir tablo olur (Google Sheets → CSV dışa aktarım → içe aktarma betiği şemayı doğrular).

## 3. Mimari ve sorumluluk sınırları

```
[Next.js PWA] --/api--> [FastAPI]
                          ├─ Kural katmanı: scheduler, curriculum-validator, validator, reports
                          ├─ LLM katmanı:   llm (müfredat taslağı, etkinlik üretimi, geri bildirim)
                          └─ Kayıt:         events (append-only) → türev tablolar
[procrastinate worker] -- gece oturum üretimi, pazar raporu + yeniden plan, başarısız işlerin tekrarı
[PostgreSQL] -- tek veritabanı: içerik + olaylar + türev durum + iş kuyruğu
[Nesne deposu] -- TTS ses dosyaları
```

Blueprint'teki "iki veri deposu" (içerik deposu ve olay/öğrenci deposu) MVP'de **tek Postgres içinde iki şema** olarak uygulanır (`content`, `learning`). Ayrı sunucu gerekmez; ayrım mantıksal kalır.

**Değişmez kurallar (kodda zorlanır):**

1. LLM hiçbir zaman türev tabloya yazmaz. LLM çıktısı → doğrulayıcı → olay/etkinlik kaydı → türev durum yalnızca olaylardan hesaplanır.
2. `events` tablosu yalnızca eklenir: uygulama rolünün `UPDATE`/`DELETE` yetkisi yoktur (veritabanı yetkisiyle zorlanır, kod disiplinine bırakılmaz).
3. `item_states` her an olay kaydından yeniden hesaplanabilir. Bir test, "artımlı güncelleme = baştan yeniden oynatma" eşitliğini sürekli doğrular.
4. Hangi öğenin çalışılacağına yalnızca `scheduler` karar verir; etkinlik üretimi bu listeyi girdi olarak alır, değiştiremez.
5. Model adı, prompt sürümü ve doğrulayıcı sonucu her üretimle birlikte saklanır.

**Tekrar motoru (uygulandı, `api/app/scheduler/`):** py-fsrs 6, hedef hatırlama 0.9, **bulanıklaştırma kapalı** (yeniden oynatma deterministik olsun diye). Derece kuralı: yanlış → Again, ipuçlu doğru → Hard, doğru → Good; Easy kullanılmıyor. Her öğe durumu işlediği son olayı (filigran) tutar; `update_item_states` artımlı ilerler, `rebuild_item_states` sıfırdan hesaplar, `find_mismatches` ikisini karşılaştırır. Olay yazan kod ve durum güncellemesi aynı kullanıcı kilidini (`lock_user`) alır. Öğe seçimi: önce vadesi gelenler (en gecikmiş önce), sonra müfredat sırasındaki yeni öğeler; tekrar birikmişse yeni öğe kotası yarıya iner.

## 4. Veri modeli (sürüm 1, 3 Kas 2026)

Üç kural: **(1)** olay bir kez yazılır, türev tablolar olaylardan yeniden üretilebilir; **(2)** her bilgi tek yerde durur, başka tablolar ona referans verir (kopya yok); **(3)** LLM'in o an ne gördüğü her zaman yeniden kurulabilir (prompt dosyası sürümü + öğrenci özeti + görev girdisi). Alan adları kodda İngilizce.

**`content` şeması** (küratörlü, sürümlü; uygulama rolü yalnızca okur)

| Tablo | Ana alanlar | Not |
| --- | --- | --- |
| `items` | id, pool_version, kind (word/chunk/structure), text_en, text_tr, cefr, sublevel, forms[], topics[], source_list, error_risk_notes, reference_sentences (jsonb), active | Seviye bir sütun (VY11); `forms` doğrulayıcı için çekimli biçimler |
| `vocab_allowlist` | lemma, cefr, forms[], source | Doğrulayıcının seviye dışı kelime kontrolü |
| `error_tags` | code, name_tr, explanation_tr, hint_template_tr, l1_related, examples (jsonb), version, active | Türkçe açıklamanın **tek** kaynağı; LLM yalnızca kod seçer |
| `fixed_tests` | id, purpose (placement/pre/post/retention), version, questions (jsonb), approved_by, approved_at | Ölçüm testleri canlı üretilmez (aşağıdaki not) |

**`learning` şeması**

| Tablo | Ana alanlar | Not |
| --- | --- | --- |
| `users` | id (UUID), email (citext), display_name, goal, daily_minutes, interests[], timezone, is_adult_confirmed, consent_version, consent_at, created_at, deleted_at | LLM'e hiçbir alanı gitmez |
| `invites`, `login_tokens`, `auth_sessions` | kod / token hash'i, son geçerlilik, kullanım ya da iptal zamanı | Düz token saklanmaz |
| `curricula` | user_id, version, weeks (jsonb), skill_weights, change_reason, llm_call_id | Her yeniden plan yeni satır |
| `study_sessions` | user_id, local_date, status, snapshot_id | Günde bir "bugünün oturumu" |
| `activity_contents` | content_hash, kind, item_ids[], cefr_sub, interest_tag, content (jsonb), audio_key, model, prompt_version, validator_version, validator_result, status, shareable, llm_call_id | Üretilen içeriğin **tek kopyası**; uygunsa kullanıcılar arasında paylaşılır |
| `activities` | user_id, session_id, content_id, origin (session/extra/template), recommended, position | Bir içeriğin bir kullanıcıya gösterimi; aynı kişiye aynı içerik bir kez (unique) |
| `events` | id (bigserial), user_id, type, occurred_at, recorded_at, activity_id, item_id, rating (FSRS 1–4), payload (jsonb), schema_version | **Tek doğruluk kaynağı**, append-only (veritabanı yetkisiyle). Öğrencinin yazdığı metin yalnızca burada |
| `feedbacks` | writing_event_id, llm_call_id, status, hint_tr, correction, validator_result | Açıklama metni saklanmaz, katalogdan okunur |
| `error_marks` | feedback_id, tag_code, span_start, span_end, shown | Hata örüntüleri buradan (ayrı `error_records` yok) |
| `item_states` | user_id + item_id, stability, difficulty, due, last_review, reps, lapses, state, last_event_id | Türev; FSRS yazar, olaylardan yeniden kurulur |
| `learner_snapshots` | user_id, content_hash, text, token_count, last_event_id | LLM'e giden öğrenci özeti; günde bir donar (Bölüm 6.2) |
| `weekly_reports` | user_id, week_start, metrics (jsonb), generated_at | Türev; kullanıcının gördüğü hali saklanır |
| `llm_calls` | user_id, purpose, model, prompt_version, snapshot_id, input/cache_read/cache_write/output token'ları, latency_ms, status, stop_reason, cost_microusd, raw_on_failure | Prompt metni saklanmaz (yeniden kurulabilir); ham yanıt yalnızca hata durumunda, 30 gün |
| `reviews` | target_type (activity_content/feedback), target_id, reviewer, verdict, wrong_teaching, notes | Işıl'ın örneklemi ve "sorun var" kuyruğu (H4) |

**Hipotezlerin verisi nerede:** H1 retention testi `fixed_tests` + events · H2 aktiflik events · H3 ön/son test `fixed_tests` + events · H4 `reviews` · H5 `feedback_reaction` olayı · H6 `nps_submitted` olayı · H7 `activities.recommended` + `extra_activity_chosen` olayı.

**Silme (KVKK/GDPR):** `users` üzerindeki kişisel alanlar boşaltılır ve `deleted_at` dolar. Events payload'undaki öğrenci metinleri, sahip rolüyle çalışan ve kendisi de kayıt bırakan tek bir `redact_user` işlemiyle silinir. Append-only kuralının tek istisnası budur.

**Olay türleri (ilk sürüm, şemalar `api/app/events/schemas.py`):** `consent_given`, `goal_set`, `fixed_test_answer`, `fixed_test_completed` (yerleştirme, ön/son ve hatırlama testleri), `curriculum_created`, `curriculum_replanned`, `activity_shown`, `answer_submitted`, `writing_submitted`, `feedback_shown`, `feedback_reaction` (anladım/anlamadım, H5), `rewrite_submitted`, `activity_flagged`, `session_completed`, `extra_activity_chosen` (öneri vs. seçim, H7), `report_viewed`, `nps_submitted` (H6). Her olay `schema_version` taşır; payload şeması Pydantic ile doğrulanır.

**Önemli teknik not – sabit testler.** Blueprint'te etkinlikler canlı üretilir; ama **yerleştirme testi, ön/son test (H3) ve 14 gün hatırlama testi (H1) canlı üretilmemeli.** Kullanıcılar arasında karşılaştırılabilir ölçüm için bu testler sabit, sürümlü ve Işıl onaylı olmalıdır. Bu yüzden `fixed_tests` tablosu eklendi. Bu, ürün dokümanındaki "Ölçüm zorlaşır" riskine doğrudan önlemdir.

## 5. Kimlik ve gizlilik

- **Akış:** e-posta girilir → (yeni kullanıcıysa davet kodu sorulur) → tek kullanımlık token e-postayla gelir → doğrulanınca `httpOnly`, `Secure`, `SameSite=Lax` oturum çerezi verilir. Oturumlar sunucu tarafında tutulur (iptal edilebilir).
- **Uygulandı (`api/app/auth/`, `api/app/deps.py`):** `POST /api/auth/request` (bilinmeyen e-postada ve davetsiz isteklerde sessizce hiçbir şey yapmaz; yalnızca geçersiz davet kodu 400 döner; e-posta başına saatte 5 bağlantı), `POST /api/auth/verify` (token tek kullanımlık ve 15 dk; yeni kullanıcıda davet ancak bu anda harcanır), `POST /api/auth/logout`, `GET /api/auth/me`. Oturum 30 gün, çerez `httpOnly` + `SameSite=Lax`, yerel dışında `Secure`. E-posta Brevo SMTP ile gider (`SmtpEmailSender`); `SMTP_HOST` boşsa (yalnızca yerelde) bağlantı loga yazılır, geliştirme dışında SMTP zorunludur. Gönderim hatasında istek 503 ile geri alınır. Davet kodu: `uv run python -m scripts.create_invites 5`.
- **Diğer uç noktalar:** `POST /api/onboarding/consent`, `POST /api/onboarding/goals`, `POST /api/feedback`, `POST /api/feedback/{id}/rewrite`, `POST /api/events` (yalnızca istemcinin bildirebileceği, derecesiz olay türleri). Onam + 18+ onayı olmadan öğrenme uç noktaları 403 döner.
- **Kayıt sırasında:** 18+ onayı, onam metni sürümü ve zamanı olay olarak kaydedilir.
- **LLM'e giden veri:** yalnızca kullanıcı UUID'si (gerekirse) ve metin. Ad/e-posta prompt'a hiç girmez; bu `llm` modülünde bir test ile zorlanır (prompt girdisinde e-posta deseni bulunursa hata).
- **Silme talebi:** kullanıcı verisi silinir, olaylar anonimleştirilir (analiz bütünlüğü için `user_id` yerine rastgele kimlik). Saklama süresi pilot öncesi yazılır (ET soruları).
- **Barındırma:** tüm servisler AB bölgesinde; LLM/TTS/e-posta sağlayıcılarında AB veri işleme ve DPA şartı aranır.

## 6. LLM katmanı

**Arayüz.** Tüm çağrılar tek giriş noktasından geçer:

```
generate_structured(purpose, prompt_id, prompt_version, inputs, output_schema, user_id) -> (parsed_output, call_meta)
```

- `output_schema` bir Pydantic modelidir; sağlayıcının yapılandırılmış çıktı (JSON şema) özelliği kullanılır, sonuç yine Pydantic ile doğrulanır.
- Model seçimi `purpose` bazında bir ayardır (`curriculum`, `session`, `extra`, `feedback`, `dialogue`). "Kolay etkinlik → ucuz model" yönlendirmesi bu tabloyla yapılır, kod değişmez.
- Her çağrı `llm_calls`'a yazılır; kullanıcı başına günlük limit buradan sayılır. Limit aşılınca yedek şablona düşülür.
- Prompt şablonları depoda sürümlü dosyalardır (`api/app/llm/prompts/<id>/v<n>.md`); sürüm etkinlik kaydına yazılır.
- Zaman aşımı + bir yeniden deneme; sonra blueprint'teki "şimdilik atladık" davranışı.

### 6.1 LLM sağlayıcı kararı (3 Kas 2026)

**Karar:** Anthropic Claude API (birinci taraf, doğrudan). İki model, `purpose` ayarıyla:

| Purpose | Model | Model ID | Neden |
| --- | --- | --- | --- |
| `session`, `extra` (etkinlik üretimi) | Claude Haiku 5.5 | `claude-haiku-5-5` | Çıktı hacmi en büyük iş; deterministik doğrulayıcı arkasında çalışıyor; çok ucuz |
| `feedback`, `dialogue` | Claude Sonnet 5.5 | `claude-sonnet-5-5` | "Yanlış öğretme %2'nin altı" (H4) en hassas hedef; Türkçe açıklama kalitesi burada belirleyici |
| `curriculum` (haftalık) | Claude Sonnet 5.5 | `claude-sonnet-5-5` | Haftada bir çağrı; kalite maliyetten önemli |

**Girdiler:** Elde bulut/AI kredisi yok (3 Kas). Pilotta LLM işleminin AB içinde olması şart değil: uygulama ve veritabanı AB'de kalır, LLM çağrıları Anthropic'in standart DPA'sı + SCC ile yapılır, ad/e-posta gönderilmez (Bölüm 5).

**Neden Claude:**

- Pydantic şemasıyla yapılandırılmış çıktı (`output_config.format` / SDK'nın `parse` yardımcısı) Python yığınımıza doğrudan oturuyor.
- Aynı sağlayıcıda iki kademe, aynı SDK: "kolay iş → ucuz model" kuralı yalnızca bir ayar.
- Erişim için satış onayı ya da kredi gerekmiyor; Hafta 1'de hemen başlanabilir.
- AB'ye geçiş yolu açık: aynı modeller Google Vertex AI (`eu` çoklu bölge) ve Amazon Bedrock (`eu.` profili) üzerinde aynı SDK ile çalışıyor (`AnthropicVertex` istemcisi). Gerekirse geçiş kod değil yapılandırma değişikliğidir; bölgesel uç noktalarda ~%10 ek ücret var.

**Pilot maliyet tahmini** (Anthropic liste fiyatları, Kas 2026: Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10 milyon token başına girdi/çıktı):

Varsayım, kullanıcı-gün başına: oturum üretimi (3k girdi / 5k çıktı), 1 ek çalışma (2.5k / 2.5k), 2 geri bildirim ya da diyalog çağrısı (her biri 1.5k / 0.8k). Düşünme (thinking) token'ları çıktıya dahil. 50 kullanıcı × 60 gün = 3.000 kullanıcı-gün → ~25M girdi, ~27M çıktı token.

| Senaryo | Pilot toplamı |
| --- | --- |
| Hepsi Haiku 5.5 | ~$16 |
| **Seçilen karışım (üretim Haiku, geri bildirim Sonnet)** | **~$79** |
| + haftalık müfredat (Sonnet) | ~$27 |
| Hepsi Sonnet 5.5 | ~$324 |
| Karşılaştırma: Gemini Flash (giriş fiyatı / 2027 fiyatı) | ~$122 / ~$243 |

**İlk ölçüm (3 Kas 2026, `api/scripts/try_feedback.py`, Sonnet 5.5, 10 tipik A1 cümlesi):** 10/10 doğrulayıcıdan geçti, hata türleri doğru, 2 doğru cümle doğru kabul edildi (aşırı düzeltme yok). Önbellek tutuyor: ilk çağrı 1.971 token yazdı, sonraki 9 çağrı aynı 1.971 token'ı okudu; önbelleksiz girdi çağrı başına ~40 token. Çıktı çoğunlukla 80–100 token (bir çağrıda 401). Maliyet: ilk çağrı $0.0088, sonrakiler ortalama ~$0.0015; toplam $0.023. Tahmindeki geri bildirim çağrısı (~$0.011) gerçekte yaklaşık 7 kat ucuz. Gecikme 1,2–8,1 sn (medyan ~2,5 sn). Hata etiketleri ve açıklamalar bu denemede taslaktı; seviye sözlüğü geçiciydi.

**Bütçe:** Geliştirme, altın set koşuları ve pilot dahil **$150 üst sınır**. Konsolda harcama limiti ayarlanır. Kullanıcı başına günlük çağrı limiti başlangıçta 20. Gerçek token sayıları `llm_calls` tablosundan Hafta 1'deki ilk örnek oturumla doğrulanır; tahmin %50'den fazla saparsa bu tablo güncellenir.

**Model API'si için uygulama notları (SDK sürümüne karşı kod yazarken doğrulanacak):**

- `temperature` / `top_p` gönderilmez; güncel API bunları reddediyor. Tekrarlanabilirlik prompt sürümü + kayıtla sağlanır.
- Düşünme (thinking) bu modellerde varsayılan olarak açık ve çıktı token'ı olarak faturalanır. Maliyet/kalite `effort` ayarıyla yönetilir (üretim için `low`, geri bildirim için `medium` ile başlanır, altın setle ayarlanır).
- `stop_reason` her yanıtta kontrol edilir (`refusal`, `max_tokens`); bunlar doğrulayıcı hatası gibi ele alınır (yeniden dene → yedek şablon).
- Sabit sistem prompt'u + hata etiketi listesi + şema, prompt önbelleğine (prompt caching) uygun sırayla yerleştirilir: değişken içerik en sonda.
- Gece oturum üretimi gecikmeye duyarsız; Batch API (%50 indirim) sonraki optimizasyon olarak açık bırakılır (sabah oturum hazır değilse `ensure_session` devreye girer).

**Ne zaman yeniden değerlendirilir:** Kapı 2'deki altın set sonucunda Sonnet 5.5 "yanlış öğretme" ya da "cevabı ele verme" eşiğini tutturamazsa, geri bildirim rotası için bir alternatif (daha güçlü bir Claude modeli ya da başka sağlayıcı) aynı altın setle karşılaştırılır. Pilot öncesi AB işleme şartı çıkarsa Vertex AI `eu` uç noktasına geçilir.

**TTS ayrı:** Anthropic TTS sunmuyor; TTS sağlayıcısı ayrı karar olarak kalıyor (Hafta 3).

### 6.2 Bağlam ve maliyet modeli

Başlangıç noktası Hermes Agent: kısa bir hafıza dosyası oturum başında sistem prompt'una **dondurulmuş** olarak girer, önek sabit kaldığı için prompt cache tutar. Bizim üç farkımız var:

1. **Hafızayı LLM yazmaz.** Öğrenci özeti (`learner_snapshots`) olaylardan deterministik olarak üretilir. Sapma olmaz, yeniden üretilebilir, "LLM öğrenci modeline yazmaz" kuralına uyar.
2. **Üç katmanlı önek.** (0) Amaç başına statik blok: rol, pedagoji kuralları, hata kodu listesi, 2–3 örnek. Tüm kullanıcılar için aynıdır, ≥512 token, `cache_control` ttl 1 saat. (1) Öğrenci özeti: ≤300 token, günde bir donar; seviye, hedef, ilgi alanları, zayıf beceri, en sık 3 hata kodu, bugünün odağı. İkinci cache kırılma noktası. (2) Görev: yalnızca bu görevin öğe kartları; geri bildirimde hedef cümle, öğrenci metni ve o öğelerdeki son 2 hata kodu.
3. **Asıl maliyet çıktıda** (pilot tahmininde ~%75). Bu yüzden çıktı da hedefleniyor:
   - Türkçe açıklama katalogdan gelir; LLM yalnızca kod, konum ve kısa ipucu döndürür.
   - Çıktı şemaları girdiyi yankılamaz; `max_tokens` ve `effort` amaç başına ayardır.
   - Doğrulanmış kısa etkinlikler (hatırlama, yeni öğe sunumu) aynı öğe + seviye + ilgi alanı için yeniden kullanılır; üretimden önce `activity_contents` aranır. Aynı kişiye aynı içerik gösterilmez. Okuma, diyalog ve geri bildirim her zaman kişiye özel üretilir.
   - Hatırlama soruları gerektiğinde `reference_sentences`'tan LLM'siz şablonla üretilir.

**Uygulama (`api/app/llm/`):** `purposes.py` (amaç → model, `max_tokens`, `effort`, Sonnet rotalarında sunucu tarafı ret yedeği), `client.py` (`LLMClient` arayüzü, Anthropic adaptörü, önbellek kırılma noktaları), `service.py` (`generate_structured`: günlük limit, e-posta koruması, `llm_calls` kaydı ve maliyet; hata istisna değil `None` döner), `snapshot.py` (öğrenci özeti), `prompts/<amaç>/<sürüm>.md`. İlk kullanıcı yazma geri bildirimi: `feedback/llm_schema.py` + `prompts/feedback/v1.md`. Katalogda `OTHER` kodunun bulunması gerekir (içerik tohumlaması).

Sıkıştırma gerekmez: çağrılar tek seferlik, tek çok turlu iş olan yazılı diyalog 4–6 turla sınırlı ve yalnızca eklenir. Gece üretimi için Batch API sonraki optimizasyondur. Her çağrının cache okuma/yazma token'ları `llm_calls`'a yazılır; cache'in tuttuğu buradan izlenir.

**CTO notu – oturumu tek çağrıda üretmek.** Blueprint "bugünün oturumu tek çağrıyla" diyor. Uzun çıktıda tek bir etkinlik doğrulamadan kalırsa tüm oturumu çöpe atmak pahalıdır. Uygulama şöyle olacak: tek çağrı tüm oturumu üretir, ama doğrulama **etkinlik bazında** yapılır; kalan etkinlikler yalnızca kendileri için yeniden üretilir, ikinci kez kalırsa yedek şablona düşer. Gece üretimi sorunsuz olduğu sürece kullanıcı bunu hissetmez.

**Doğrulayıcı (deterministik, LLM'siz):**

| Kontrol | Uygulama |
| --- | --- |
| Şema | Pydantic modeli |
| Seviye dışı kelime | A1–A2 izinli kelime listesi + öğe havuzu + basit çekim tablosu; liste dışı kelime oranı eşiği |
| Hedef öğe kullanımı | Hedef öğenin metinde (çekimli biçimleri dahil) geçtiği kontrolü |
| Cevap sızıntısı | Doğru cevabın soru metninde/ipucunda geçmemesi |
| Tek doğru cevap | Çoktan seçmelide şıkların tekilliği, boşluk doldurmada kabul edilen cevap kümesi |
| Ses–metin uyumu | TTS'e giden metin = ekranda doğrulanan metin |
| Geri bildirim | Etiket sabit kümeden mi, en fazla 2 hata gösteriliyor mu, ipucu doğru cümleyi içeriyor mu |

**Uygulandı (`api/app/validator/`):** `core.py` (sonuç tipi, sözcükleme, `vocab_allowlist` + öğe biçimlerinden seviye sözlüğü), `feedback.py` (tutarlılık, katalog kodu, konum, ipucu ≤120 karakter, ipucunda düzeltme kelimesi yok, düzeltme öğrencinin cümlesine ≥0.5 benzer ve seviye içinde; gösterilen hata en fazla 2), `activity.py` (seviye, hedef öğe, cevap sızıntısı, tek doğru şık, ses–metin uyumu, uzunluk). Bilinen sınır: cümle başındaki özel isim sıradan kelimeden ayırt edilemez; üretici kullandığı isimleri izinli kelime olarak verir.

**Geri bildirim akışı (uygulandı, `api/app/feedback/service.py`):** `give_feedback` öğrencinin metnini `writing_submitted` olayı olarak yazar → günün donmuş öğrenci özetiyle Sonnet'e sorar → doğrulayıcıdan geçirir → `feedbacks` + `error_marks` kaydeder. Geçerse birincil hedef öğe için `writing_assessed` olayı (doğru → Good, yanlış → Again) yazılır ve tekrar motoru güncellenir; geçmezse (limit, API hatası, ret, doğrulayıcı) öğrenci "şimdilik atladık" görür, öğrenci modeli değişmez. Doğru cümle yalnızca `submit_rewrite` ile, yeniden yazmadan sonra döner. Bekleyen (`deferred`/`rejected`) geri bildirimleri yeniden işleyen iş henüz yok.

**Seviye listesi (karar, 3 Kas 2026): CEFR-J Wordlist Version 1.6** (Tono Laboratuvarı, Tokyo Yabancı Diller Üniversitesi). Resmi sayfaya göre atıfla araştırma ve ticari kullanım ücretsiz, türetilmiş liste serbest. EVP elendi: ticari kullanım yazılı izin gerektiriyor. İçe aktarma `scripts/import_cefrj.py`: 7.035 kelime (A1 1.088, A2 1.272, B1 2.178, B2 2.497), kelime başına en düşük seviye; düzensiz biçimler (went, children, better) içe aktarmada lemminflect (MIT) ile üretilir, doğrulayıcı düzenli ekleri ayrıca çözer. Doğrulayıcı A1+A2'yi kullanır. Kaynak dosya depoya konmaz (yeniden dağıtım açıkça düzenlenmemiş); atıf panelde ve README'de.

**Altın set.** `eval/golden/` altında Işıl'ın etiketlediği ~100 cümle (JSONL). `uv run python -m eval.golden --purpose feedback` komutu blueprint Bölüm 7'deki beş ölçütü raporlar. Prompt ya da model değişikliği bu rapor olmadan birleştirilmez.

## 6.3 Arayüz (uygulandı, `web/`)

Ekranlar: `/login` (e-posta + davet kodu), `/auth/verify`, `/onboarding/consent` (taslak KVKK metni), `/onboarding/goals`, `/panel` ("Bugünün oturumu" ve ek çalışmalar; şimdilik yalnızca yazma açık), `/practice/writing` (yaz → ipucu + katalog açıklaması + anladım/anlamadım → yeniden yaz → doğrusu; "sorun var" bağlantısı). Yönlendirme her zaman onam → hedef → panel sırasını zorlar. Tipler FastAPI şemasından üretilir: `npm run gen:api`. Geliştirme içeriği (taslak hata etiketleri, 10 öğe, küçük A1 kelime listesi): `uv run python -m scripts.seed_dev_content`. Yazma görevi şimdilik geçici `GET /api/practice/writing-task` ile gelir; etkinlik üretimi gelince `activity_contents`'ten gelecek.

## 6.4 Etkinlik üretimi (uygulandı, `api/app/sessions/`)

- **Akış (`generation.py`):** tekrar motoru öğeleri seçer (günlük süreye göre en fazla 6 tekrar + 3 yeni; 15 dk) → kısa türlerde (hatırlama, yeni öğe) başkası için üretilmiş onaylı içerik yeniden kullanılır → kalanlar için tek Haiku çağrısı (`prompts/session/v2.md`) → her etkinlik ayrı doğrulanır (`validation.py`) → kalanlar için bir çağrı daha → yine kalırsa LLM'siz şablon (`templates.py`; okuma için şablon yok, oturumdan çıkar). Reddedilen her çıktı `status = rejected` ile saklanır (Işıl'ın denetimi için).
- **Türler:** yeni öğe (anlam + 2 örnek + kontrol sorusu), hatırlama (3 şıklı boşluk doldurma + Türkçe ipucu), mikro okuma (50–80 kelime + 2 soru), yazma görevi. Dinleme (TTS) henüz yok; yazılı diyalog ek çalışmada (6.11).
- **Değerlendirme (`service.py`):** cevap sunucuda değerlendirilir; öğrenciye giden görünümde cevap yoktur. Derece: yanlış → Again, ipuçlu doğru → Hard, doğru → Good; okuma soruları derecelendirilmez. Aynı soru iki kez sayılmaz. Tüm etkinlikler bitince `session_completed`.
- **Uç noktalar:** `GET /api/session/today`, `POST /api/activities/{id}/answer`; `POST /api/feedback` oturum etkinliğinde görevi sunucudaki içerikten okur.
- **İlk gerçek ölçüm (3 Kas 2026, geliştirme içeriğiyle):** oturum başı ~$0.003 (2 Haiku çağrısı; ikincisi önbellekten 2.958 token okudu). Süre ~23 sn: kullanıcı bekletilemez, **gece ön üretimi (procrastinate işi) pilot öncesi şart**. Reddedilen 5 çıktının hepsi seviye kontrolündendi: çekim kuralları (`friends→friend`, `watching→watch`) eklendi ve geliştirme kelime listesi genişletildi; aynı 5 çıktı yeniden doğrulamada geçti. Gerçek seviye listesi (EVP ya da açık frekans listesi) hâlâ açık karar.

## 6.5 Gece ön üretimi (uygulandı)

- **Kuyruk:** procrastinate, kendi `procrastinate` şemasında (göç 0003; bağlantı `search_path` ile görür). Worker: `uv run python -m app.worker` (Windows'ta psycopg'nin asenkron modu için Selector döngüsü açıkça seçilir).
- **İşler (`app/jobs.py`):** `schedule_sessions` 15 dakikada bir çalışır ve `app/sessions/scheduling.py` kuralıyla seçilen kullanıcılar için `generate_session` işini kuyruğa koyar (kullanıcı + gün başına tek iş, `queueing_lock`). `generate_session` 3 deneme hakkıyla `ensure_session`'ı çağırır; tekrar çalışması LLM'e ikinci kez gitmez.
- **Seçim kuralı:** yerel saat 03:00'ü geçmiş, onam + hedef tamam, son 7 günde aktif (ya da yeni kayıt) ve bugünün oturumu hazır değil. 7 günden uzun süredir gelmeyen kullanıcıya para harcanmaz; döndüğünde oturum istek anında üretilir.
- **İlk gerçek çalışma (3 Kas 2026):** yeni bir kullanıcı için oturum arka planda 16,6 sn'de üretildi (2 Haiku çağrısı), öğrenci beklemedi. Ancak oturum zayıf çıktı (4 etkinlik, 2'si şablon, okuma yok): reddedilen 7 çıktının hepsi seviye kontrolündendi (cat, near, museum, flat, things...). Neden küçük geliştirme listesiydi. **CEFR-J'ye geçince** aynı profil (seyahat, yemek + müzik) için oturum tek Haiku çağrısında, 10,9 sn'de, $0.0011'e, 0 ret ile üretildi: 5 etkinliğin hepsi LLM'den, okuma dahil. Önceki 12 ret yeniden doğrulandı: 9'u geçti, kalan 3'ü gerçekten B1 kelimeler (jazz, spicy, strawberries).

## 6.6 Yerleştirme testi (uygulandı)

- **Sorular (`api/scripts/placement_v1.py`, TASLAK):** 24 özgün soru, A1 ve A2'den 12'şer: kelime, yapı, iki kısa okuma metni. Dinleme TTS seçilince eklenecek (sürüm 2). Pilot öncesi Işıl onayı gerekli; onaylanınca `fixed_tests.approved_by/approved_at` doldurulur. İçerik değişirse yeni sürüm açılır (eski cevaplar eski sürüme bağlı kalır).
- **Puanlama (`app/onboarding/placement.py`):** A1 < %50 → "pre-A1"; değilse A2 < %50 → A1; değilse A2. Alt seviye: kendi seviyesinde ≥ %80 ise 2, değilse 1. "Bilmiyorum" yanlış sayılır. pre-A1 öğrenci A1.1'den başlar.
- **Akış (`app/onboarding/fixed_tests.py`):** her cevap `fixed_test_answer`, sonuç `fixed_test_completed` olayı; test sırasında doğru cevap gösterilmez, cevaplar tekrar motorunu etkilemez, yarıda kalan test kaldığı yerden sürer. Şıklar kullanıcıya özgü ama sabit sırayla karıştırılır: taslak bankada doğru cevap çoğunlukla ilk şıktaydı ve tarayıcı denemesinde fark edildi.
- **Etkisi:** onboarding sırası onam → hedef → yerleştirme → panel. Oturum üretiminde A1 öğrencisine yalnızca A1 öğeleri, A2 öğrencisine önce A2 öğeleri gelir; paylaşılan içerik alt seviyeye (`A1.1`, `A2.2`…) göre eşleşir.
- **H3:** aynı sabit test ön test olarak kullanılabilir; son test için aynı mekanizma `purpose = 'post'` ile çalışır (henüz içerik yok).
- **Uç noktalar:** `GET /api/onboarding/placement`, `POST /api/onboarding/placement/answer`, `POST /api/onboarding/placement/complete`.

## 6.7 Müfredat ajanı (uygulandı, `api/app/curriculum/`)

- **Öneri:** Sonnet 5.5 (`prompts/curriculum/v1.md`) öğrenci özeti, haftalık kapasite ve tüm öğe havuzunu (id, İngilizce, Türkçe, seviye) alır; 8 haftalık plan döner: haftalık odak, öğeler, 1–3 Türkçe "yapabilirim" maddesi, beceri ağırlıkları, kısa özet.
- **Kural katmanı (`rules.py`):** tam 8 hafta; yalnızca havuzdaki öğeler; her öğe bir kez; hafta başına en fazla kapasite (günlük yeni öğe × 6 gün; kota tek yerde, `scheduler/quotas.py`); havuz ile 8 haftalık kapasiteden küçük olanının en az %80'i planlanmış; odak ve "yapabilirim" dolu. Ağırlık toplamı, metin uzunlukları gibi küçük kusurlar düzeltilir. Ret sebepleri ajana geri verilip bir kez daha sorulur; yine geçmezse deterministik yedek plan (havuz sırası haftalara bölünür) kaydedilir. Öğrenci her durumda plan görür.
- **Kayıt:** her plan `curricula`'da yeni sürüm; kaynak (agent / fallback), özet ve genel ağırlıklar plan satırında; `curriculum_created` / `curriculum_replanned` olayı.
- **Etkisi:** oturum üretimi yeni öğeleri müfredat sırasıyla alır: bu haftanın öğeleri, sonra sonraki haftalar, en son geride kalanlar.
- **Ekran:** `/curriculum` içindekiler gibi; şu anki hafta işaretli (yeniden planda numara sıfırlanmaz, sürüm kadar kayar), süre "tahmin" olarak gösterilir (SK6). Panelde "Planın" bağlantısı.
- **İlk gerçek çalışma (4 Kas 2026):** ilk denemede kurallardan geçti, 9,0 sn, ~$0.02; geliştirme havuzu yalnızca 10 öğe olduğu için haftalar 2'şer öğe. Temalar hedef ve ilgi alanlarıyla uyumlu ("İşimi ve yaşadığım yeri tanıtma", "Sevdiklerim: futbol ve yemek"), son haftalar pekiştirme.
- **Haftalık yeniden planlama:** aşağıdaki 6.8.

## 6.8 Haftalık rapor ve yeniden planlama (uygulandı, `api/app/reports/`)

- **Metrikler (`service.py`)**, kullanıcının yerel pazartesi–pazar penceresinde yalnızca olaylardan: aktif gün, tamamlanan oturum, yeni öğe (ilk kez derecelendirilen), kalıcılaşan öğe (Review durumunda ve kararlılık ≥ 7 gün), tekrar başarısı (Hard ve üstü oranı), beceri başına dakika (cevap süreleri; yazma için 1,5 dk tahmin), "anladım" oranı (H5), ek çalışma seçimi (H7), en sık hata (katalog açıklamasıyla). Rapor bir kez yazılır.
- **Tempo:** başarı < %60 → yavaş (haftalık kapasite × 0,75), ≥ %90 ve ≥ 4 oturum → hızlı (× 1,25), az veride normal.
- **Yeniden planlama (`weekly.py`):** hafta aktifse müfredat ajanı ilerleme özetiyle yeniden çalışır: derecelendirilmiş olayı olan öğeler havuzdan çıkar, kapasite tempoya göre ayarlanır, `summary_tr` değişikliği ve nedenini söyler (blueprint: "değişiklik nedeniyle birlikte gösterilir"). Hiç gelmeyen kullanıcıya LLM çağrısı yapılmaz; rapor yine yazılır, plan aynı kalır.
- **İş:** `schedule_weekly_reviews` saatte bir; yerel pazar 20:00 sonrası, raporu olmayan kullanıcılar için kullanıcı + hafta başına tek `weekly_review` işi.
- **Ekran:** `/report` (tarih aralığı, dört gösterge, beceri dağılımı, en sık hata, plan değişikliği); panelde rapor varsa bağlantı. `GET /api/reports/latest`.
- **İlk gerçek çalışma (4 Kas 2026):** 8,2 sn, tek Sonnet çağrısı; değişiklik açıklaması somut ve hatalara dayalı. İki ifade sorunu vardı: rapor pazar günü aynı hafta için üretildiği hâlde "geçen hafta" dedi; "artikel" yerine İngilizce "article" kullandı. **Düzeltildi (müfredat prompt v2):** Türkçe metinde İngilizce dilbilgisi terimi yasak (kural katmanı da `english_jargon` ile reddeder), yeniden planlamada "bu hafta" dili ve ilk cümlede değişikliğin sayıya dayalı nedeni. Aynı kullanıcı/hafta için yeniden denendi: "Bu hafta tekrar başarın 0,57 olduğu için planı yavaşlattım ve artikel (a/an/the) çalışmasını artırdım." İlk denemede kurallardan geçti (15 sn, ~$0.03).

## 6.9 Bekleyen geri bildirim (uygulandı)

- **Yeniden deneme (`app/feedback/retry.py`):** gösterilemeyen yazılar (günlük limit, API hatası, ret, doğrulayıcıdan kalma) saatlik `schedule_feedback_retries` işiyle yeniden değerlendirilir; yazı başına tek iş. Sınırlar: en fazla 7 günlük yazı, en fazla 3 deneme; sonra bırakılır (denetimde `rejected`/`deferred` kayıtlar olarak kalır). Her deneme yeni bir `feedbacks` satırıdır, geçmiş korunur.
- **Görev metni saklanmaz:** etkinlikteki yazma görevinden ya da serbest pratik şablonundan yeniden kurulur. Değerlendirme, ilk gönderimle aynı yoldan geçer (`assess_writing`): doğrulayıcı, hata işaretleri, derece olayı, tekrar motoru.
- **Öğrenciye:** gecikmeli hazırlanan ve henüz görülmemiş geri bildirimler `GET /api/feedback/ready` ile gelir; panelde "Geri bildirimlerin hazır (n)" kartı, `/feedback` sayfasında aynı akış (işaretli cümle → ipucu → açıklama → anladım/anlamadım → yeniden yaz → doğrusu). Görüldüğünde `feedback_shown` olayı `feedback_id` ile yazılır ve liste bir daha göstermez.
- **Gerçek deneme (4 Kas 2026):** kesinti benzetimiyle ertelenen "My brother like football very much." saatlik işin yolundan Sonnet ile yeniden değerlendirildi: TENSE (üçüncü tekil -s), panelde göründü, yeniden yazmadan sonra doğrusu gösterildi, görülünce kart kalktı.

## 6.10 Ek çalışma (uygulandı, `api/app/sessions/extra.py`)

- **Türler:** Tekrar ve Okuma talep anında üretilir; Yazma şablon görevle (öğe tekrar motorundan); Yazılı diyalog için bkz. 6.11. Dinleme (TTS) henüz yok, panelde "yakında".
- **Öğeler kural katmanından:** önce vadesi gelen tekrarlar, sonra en zorlanılanlar (çok unutulan, düşük kararlılık). Hiç öğe görülmemişse ek çalışma açılmaz ("önce bugünün oturumunu yap").
- **Aynı üretim hattı:** oturumdan ayrıştırılan `build_activities` (yeniden kullanım → Haiku → etkinlik başına doğrulama → bir kez daha → şablon → kayıt). Ek çalışma etkinlikleri `origin = extra`, oturuma bağlı değil; cevaplar aynı sunucu değerlendirmesinden geçer.
- **"Önerilen" (H7):** müfredatın bu haftaki beceri ağırlığı ile bu hafta gerçekten ayrılan süre arasındaki en büyük açık. Her seçimde `extra_activity_chosen` olayı (önerilen ve seçilen tür) yazılır; etkinlikteki `recommended` alanı seçimin öneriyle aynı olup olmadığını tutar.
- **Uç noktalar ve ekran:** `GET /api/practice/recommendation`, `POST /api/practice/extra`; `/practice/recall`, `/practice/reading`. Oturum ve ek çalışma aynı `ActivityQueue` bileşenini kullanır.
- **Gerçek deneme (4 Kas 2026):** Okuma önerildi (hafta içinde okumaya hiç zaman ayrılmamıştı); Tekrar seçildi (4 soru, 3,4 sn), sonra Okuma (6,4 sn); ikisi de < $0.001, seçimler ve öneri ayrı kaydedildi.

## 6.11 Yazılı diyalog (uygulandı, `api/app/dialogue/`)

- **Kural katmanı seçer:** senaryo hedefe göre (`scenarios.py`; amaç başına 3 günlük durum, kullanıcının önceki diyalog sayısıyla döner), hedef öğeler ek çalışmayla aynı yerden (vadesi gelen, sonra zorlanılan; en fazla 2, hiç öğe yoksa hedefsiz). Senaryo metinleri ve açılış cümleleri sabit (taslak, **Işıl onayı bekliyor**): diyalog LLM'siz, anında başlar.
- **Tur başına tek Sonnet çağrısı** (`purpose = dialogue`, prompt `dialogue/v1`): öğrencinin son cümlesine yazma geri bildirimiyle aynı şemada değerlendirme + partnerin sıradaki cümlesi + `done`. Statik blok (rol, kurallar, hata kataloğu) 1 saatlik önbellekte; görev bloğu konuşmayı baştan sona yalnızca ekleyerek taşır.
- **Doğrulama:** geri bildirim yazma doğrulayıcısından (`validate_feedback`) geçer; geçemezse gösterilmez ve ertelenmez (canlı konuşmada sonradan düzeltme işe yaramaz; yeniden deneme işi diyalog cümlelerini atlar). Partner cümlesi seviye kontrolünden geçer (izinli isimler/şehirler, hedef öğeler ve öğrencinin kendi kelimeleri serbest; 1–20 kelime; Türkçe çevirisi dolu). Geçemezse bir kez daha istenir, sonra sabit cümle ("I see. Can you tell me more?" / 4. turdan sonra kapanış). Reddedilen partner cümleleri `dialogue_partner_rejected` olarak loglanır.
- **Tur sınırları kural katmanında:** en az 4, en fazla 6 öğrenci cümlesi; model 4'ten önce bitiremez, 6. turda bitirmesi istenir ve diyalog her durumda kapanır. Biten diyaloğa cevap 409.
- **Kayıt:** öğrencinin cümlesi `writing_submitted`, partnerin cevabı `dialogue_replied` olayı (tur, geri bildirim id'si, cümle, kaynak llm/fallback, bitti mi). Konuşma geçmişi yalnızca olaylardan kurulur. Diyalog içeriği `activity_contents`'te `kind = dialogue` (paylaşılmaz), etkinlik `origin = extra`; seçim `extra_activity_chosen` ile kaydedilir (H7). Diyalog cümleleri FSRS derecesi üretmez (hedef öğeyi sınamak için yazılmıyor); hata işaretleri haftalık rapordaki en sık hataya girer.
- **Ekran (`/practice/dialogue`):** senaryo kartı, sohbet balonları (partner cümlesinin Türkçesi istenince), her öğrenci cümlesinin altında kısa geri bildirim: işaret + ipucu, "Açıklamayı göster" ile katalog açıklaması ve anladım/anlamadım (H5). Doğru cümle gösterilmez; konuşma akmaya devam eder.
- **Gerçek deneme (4 Kas 2026, iş senaryosu):** 5 turda doğal kapanış; 2 hata (ARTICLE, TENSE) ipucuyla işaretlendi, 3 cümle doğru, tüm geri bildirimler doğrulayıcıdan geçti. 6 çağrı (bir partner cümlesi yeniden istendi), 2–5 sn; ilk çağrı önbellek yazımıyla ~$0.011, sonrakiler ~$0.002 (2.224 token önbellekten); diyalog başına ~$0.026. **Gözlem:** "I work as engineer" cümlesinde artikel işareti bir kelime erken kondu (model karakter konumunu kaydırdı); 6.12'de düzeltildi.

## 6.12 Hata yeri sunucuda bulunur (geri bildirim v2, diyalog v2)

- **Sorun:** model hata yerini karakter konumu (`start`/`end`) olarak verince konumu kaydırabiliyor; doğrulayıcı yalnızca sınırları kontrol edebildiği için yanlış yerdeki işaret öğrenciye gidiyordu.
- **Çözüm:** LLM şeması artık konum istemez. Model hatalı kelime(ler)i olduğu gibi alıntılar (`quote`) ve eksik kelimede boşluğun alıntının önünde mi arkasında mı olduğunu söyler (`gap`: none/before/after). Konumu sunucu bulur (`app/validator/feedback.py: span_of`): kelime sınırında, büyük/küçük harf ve boşluk farkı gözetmeden, ilk geçtiği yer. Alıntı metinde yoksa geri bildirim reddedilir (`quote_not_found`). `error_marks` ve arayüz değişmedi (konumlar yine orada).
- **Prompt'lar:** `feedback/v2`, `dialogue/v2` (v1 dosyaları eski `llm_calls` kayıtları için duruyor). Aynı kelime birden çok geçiyorsa model iki-üç kelime alıntılar.
- **Gerçek deneme (4 Kas 2026):** yazma geri bildirimi setinde 10/10 doğrulayıcıdan geçti (~$0.0225, önbellekten 2.277 token); diyalogda "I work as engineer here." artikel işareti doğru yerde ("engineer" önü).

## 7. Arka plan işleri ve zamanlama

| İş | Ne zaman | Ne yapar |
| --- | --- | --- |
| `pregenerate_sessions` | Her gece, kullanıcının saat dilimine göre ~03:00 (varsayılan Europe/Istanbul) | Scheduler'dan yarının öğelerini alır → oturumu üretir → doğrular → TTS seslerini üretip depoya yazar |
| `ensure_session` | Kullanıcı panele gelip oturumu hazır değilse | Aynı işi talep anında çalıştırır (yükleme ekranı) |
| `weekly_report_and_replan` | Pazar gecesi | Haftalık raporu olaylardan hesaplar, müfredat ajanını çağırır, kural katmanı doğrular, yeni müfredat sürümü yazar |
| `retry_deferred_feedback` | Saatlik | "Şimdilik atladık" ile kaydedilen yazmaları yeniden işler |
| `retention_test_due` | Günlük | 14 gün dolan öğeler için hatırlama testi planlar (H1) |

## 8. Test ve kalite stratejisi

- **Birim test (pytest), zorunlu:** scheduler (FSRS sarmalayıcı), müfredat kural doğrulayıcı, etkinlik doğrulayıcı, olay yeniden oynatma eşitliği, günlük limit, prompt'ta kişisel veri olmaması.
- **LLM'li testler:** CI'da çalışmaz; kayıtlı sağlayıcı yanıtlarıyla (fixture) test edilir. Gerçek çağrı yalnızca altın set betiğinde.
- **Arayüz:** kritik akış için tek bir Playwright duman testi (giriş → oturum → yazma → geri bildirim). Bileşen testleri yalnızca mantık içeren yerlerde.
- **Statik kontrol:** ruff (lint + format), mypy (strict, `app/` için), ESLint + `tsc`.
- **CI:** GitHub Actions; her push'ta lint + tip + test + `next build`.

## 9. Geliştirme ortamı

Bu makine (Windows 10, 6 GB RAM, Ryzen 5 3500U) için hafif kurulum: Docker yok, PostgreSQL servis olarak doğrudan kurulur.

| Araç | Sürüm | Kurulum | Durum (3 Kas 2026) |
| --- | --- | --- | --- |
| Git | 2.56.0 | winget `Git.Git` | Kuruldu |
| Node.js LTS | 26.13.0 (npm 11.20) | winget `OpenJS.NodeJS.LTS` | Kuruldu. npm 12 çıktı ama Node ile gelen sürümde kalınıyor |
| uv | 0.13.7 | winget `astral-sh.uv` | Kuruldu (en güncel) |
| Python | 3.14.10 | `uv python install 3.14.10 --default` | Kuruldu, `~/.local/bin` PATH'te |
| PostgreSQL | 18.6 | winget `PostgreSQL.PostgreSQL.18` (yalnızca sunucu + komut satırı araçları; pgAdmin yok) | Kuruldu, servis `postgresql-x64-18`, port 5432, `bin` PATH'te. Süper kullanıcı şifresi `.secrets/postgres-local.env` (depoya girmez) |
| VS Code | mevcut | — | Vardı |
| GitHub CLI | — | winget `GitHub.cli` | Kurulmadı; depo açılınca |

**Neden Python 3.14, 3.15 değil:** 3.15 yeni çıktı; psycopg, pydantic-core gibi derlenmiş paketlerin tüm Windows tekerlekleri henüz garanti değil. 3.14 bir yıllık ve 2030'a kadar destekli.

Proje bağımlılıkları (`next`, `fastapi` vb.) iskelet kurulurken `npm` ve `uv` ile projeye eklenir; global kurulmaz.

**Yerel veritabanı düzeni:** `postgres` süper kullanıcısı yalnızca yönetim için. Uygulama için ayrı roller: `teacher_owner` (Alembic göçleri) ve `teacher_app` (çalışma zamanı; `events` üzerinde `UPDATE`/`DELETE` yetkisi yok). Veritabanı adları: `teacher_dev`, `teacher_test`. Bağlantı bilgileri `.env` dosyasında, depoya girmez.

## 10. Açık teknik kararlar

| Karar | Seçenekler | Ölçüt | Son tarih |
| --- | --- | --- | --- |
| ~~LLM sağlayıcısı~~ | **Karar verildi (3 Kas 2026):** Anthropic Claude API, Sonnet 5.5 + Haiku 5.5 | Bkz. Bölüm 6.1 | — |
| TTS sağlayıcısı | Ayrı TTS servisi (Anthropic TTS sunmuyor) | Ses kalitesi (yavaş, net İngilizce), fiyat, AB | Hafta 3 |
| ~~E-posta servisi~~ | **Karar verildi (4 Kas 2026):** Brevo (Fransa, AB'de işleme; günde 300 ücretsiz). Kod yalnızca SMTP konuşur (`app/auth/email.py`), sağlayıcı bir ayardır. **Açık:** gönderim için alan adı + SPF/DKIM (proje adı kararıyla birlikte); alan adı olmadan e-postalar spam'e düşer | — | Alfa öncesi |
| Barındırma | Tek platformda API + worker + Postgres (AB) ve arayüz için Next.js uyumlu AB bölgesi | Kurulum kolaylığı, maliyet, AB, yedekleme | Alfa öncesi (~Hafta 9) |
| ~~İzinli kelime listesi kaynağı~~ | **Karar verildi (3 Kas 2026):** CEFR-J Wordlist 1.6 | Bkz. Bölüm 6 | — |
| Proje adı / alan adı | — | — | Barındırmadan önce |

## 11. Teknik yapım sırası (ilk adımlar)

Blueprint'teki ilk üç işle uyumlu:

1. **Hafta 1:** depo iskeleti (web + api), Alembic ile ilk şema (`users`, `items`, `error_tags`, `events`, `activities`, `item_states`, `llm_calls`), Anthropic API anahtarı + harcama limiti, örnek bir oturumla gerçek token maliyetinin ölçülmesi, içerik içe aktarma formatının Işıl'la netleşmesi.
2. **Hafta 2:** scheduler (FSRS) + birim testler, olay yeniden oynatma, magic link girişi, onam ekranı.
3. **Hafta 3–4:** yerleştirme testi (sabit), müfredat ajanı + kural doğrulayıcı, oturum üretimi + doğrulayıcı, gece işi.
4. **Hafta 5–6:** yazma geri bildirimi + hata etiketleri + altın set betiği (Kapı 2 hazırlığı).
5. Sonrası: TTS/dinleme, panel ve "Ek çalışma", haftalık rapor, yazılı diyalog (esnek), duman testi, barındırma, alfa.

Her hafta sonu Işıl demosu; kararlar `MD files/` altında tek satırlık karar kaydına yazılır.
