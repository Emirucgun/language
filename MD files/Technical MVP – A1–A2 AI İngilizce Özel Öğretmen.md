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

## 4. Veri modeli (ilk sürüm)

Blueprint Bölüm 5'teki varlıkların tablo karşılığı. Alan adları kodda İngilizce olur.

| Tablo | Şema | Ana alanlar | Not |
| --- | --- | --- | --- |
| `users` | learning | id (UUID), email, display_name, goal, daily_minutes, interests (jsonb), timezone, is_adult_confirmed, consent_at, consent_version, started_at, deleted_at | LLM'e yalnızca `id` gider |
| `invites` | learning | code, created_by, used_by, used_at | Pilot davet kapısı |
| `login_tokens` | learning | token_hash, user_id/email, expires_at, used_at | 15 dk geçerli, tek kullanımlık; düz token saklanmaz |
| `items` | content | id, kind (word/chunk/structure), text_en, text_tr, cefr (A1/A2…), sublevel, source_list, error_risk_notes, reference_sentences (jsonb), pool_version, active | Seviye bir sütundur (VY11) |
| `error_tags` | content | code, name_tr, explanation_tr, l1_related, examples (jsonb), version | Sabit küme; LLM yalnızca bu kodlardan seçer |
| `fixed_tests` | content | id, purpose (placement/pre/post/retention), version, questions (jsonb) | **Ekleme**, bkz. not aşağıda |
| `curricula` | learning | user_id, version, weeks (jsonb), skill_weights, change_reason, proposed_by_model, prompt_version, validated_at | Her yeniden plan yeni satır |
| `events` | learning | id (bigserial), user_id, occurred_at, type, item_id, activity_id, result, duration_ms, payload (jsonb), schema_version | Append-only |
| `activities` | learning | id, user_id, kind, item_ids, content (jsonb), audio_keys, model, prompt_version, is_recommended, origin (session/extra), validator_result (jsonb), flagged_issue, created_at | Üretilen her şey tam metin |
| `item_states` | learning | user_id, item_id, stability, difficulty, last_review, due, retrievability, reps, lapses | Türev; FSRS yazar |
| `error_records` | learning | event_id, tag_code, span, sentence, correction, student_reaction | Hata örüntüleri buradan |
| `weekly_reports` | learning | user_id, week_start, metrics (jsonb), focus, generated_at | Türev; yeniden üretilebilir |
| `llm_calls` | learning | id, user_id, purpose, provider, model, prompt_version, input_tokens, output_tokens, latency_ms, status, cost_estimate, created_at | **Ekleme.** Maliyet, günlük limit ve gecikme ölçümü buradan |

**Olay türleri (ilk sürüm):** `consent_given`, `goal_set`, `placement_answer`, `placement_completed`, `curriculum_created`, `curriculum_replanned`, `activity_shown`, `answer_submitted`, `writing_submitted`, `feedback_shown`, `feedback_reaction` (anladım/anlamadım, H5), `rewrite_submitted`, `activity_flagged`, `session_completed`, `extra_activity_chosen` (öneri vs. seçim, H7), `report_viewed`, `nps_submitted` (H6). Her olay `schema_version` taşır; payload şeması Pydantic ile doğrulanır.

**Önemli teknik not – sabit testler.** Blueprint'te etkinlikler canlı üretilir; ama **yerleştirme testi, ön/son test (H3) ve 14 gün hatırlama testi (H1) canlı üretilmemeli.** Kullanıcılar arasında karşılaştırılabilir ölçüm için bu testler sabit, sürümlü ve Işıl onaylı olmalıdır. Bu yüzden `fixed_tests` tablosu eklendi. Bu, ürün dokümanındaki "Ölçüm zorlaşır" riskine doğrudan önlemdir.

## 5. Kimlik ve gizlilik

- **Akış:** e-posta girilir → (yeni kullanıcıysa davet kodu sorulur) → tek kullanımlık token e-postayla gelir → doğrulanınca `httpOnly`, `Secure`, `SameSite=Lax` oturum çerezi verilir. Oturumlar sunucu tarafında tutulur (iptal edilebilir).
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

**Bütçe:** Geliştirme, altın set koşuları ve pilot dahil **$150 üst sınır**. Konsolda harcama limiti ayarlanır. Kullanıcı başına günlük çağrı limiti başlangıçta 20. Gerçek token sayıları `llm_calls` tablosundan Hafta 1'deki ilk örnek oturumla doğrulanır; tahmin %50'den fazla saparsa bu tablo güncellenir.

**Model API'si için uygulama notları (SDK sürümüne karşı kod yazarken doğrulanacak):**

- `temperature` / `top_p` gönderilmez; güncel API bunları reddediyor. Tekrarlanabilirlik prompt sürümü + kayıtla sağlanır.
- Düşünme (thinking) bu modellerde varsayılan olarak açık ve çıktı token'ı olarak faturalanır. Maliyet/kalite `effort` ayarıyla yönetilir (üretim için `low`, geri bildirim için `medium` ile başlanır, altın setle ayarlanır).
- `stop_reason` her yanıtta kontrol edilir (`refusal`, `max_tokens`); bunlar doğrulayıcı hatası gibi ele alınır (yeniden dene → yedek şablon).
- Sabit sistem prompt'u + hata etiketi listesi + şema, prompt önbelleğine (prompt caching) uygun sırayla yerleştirilir: değişken içerik en sonda.
- Gece oturum üretimi gecikmeye duyarsız; Batch API (%50 indirim) sonraki optimizasyon olarak açık bırakılır (sabah oturum hazır değilse `ensure_session` devreye girer).

**Ne zaman yeniden değerlendirilir:** Kapı 2'deki altın set sonucunda Sonnet 5.5 "yanlış öğretme" ya da "cevabı ele verme" eşiğini tutturamazsa, geri bildirim rotası için bir alternatif (daha güçlü bir Claude modeli ya da başka sağlayıcı) aynı altın setle karşılaştırılır. Pilot öncesi AB işleme şartı çıkarsa Vertex AI `eu` uç noktasına geçilir.

**TTS ayrı:** Anthropic TTS sunmuyor; TTS sağlayıcısı ayrı karar olarak kalıyor (Hafta 3).

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

İzinli kelime listesinin kaynağı EVP lisans sonucuna bağlı (Faz 0). Lisans uygun değilse açık bir frekans listesi + Işıl'ın havuzu ile kendi listemiz türetilir. Lemmatizasyon MVP'de basit tutulur; yetmezse spaCy değerlendirilir.

**Altın set.** `eval/golden/` altında Işıl'ın etiketlediği ~100 cümle (JSONL). `uv run python -m eval.golden --purpose feedback` komutu blueprint Bölüm 7'deki beş ölçütü raporlar. Prompt ya da model değişikliği bu rapor olmadan birleştirilmez.

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
| E-posta servisi | AB'de işleyen transactional servisler | Teslim oranı, ücretsiz kota, DPA | Hafta 2 (giriş akışından önce) |
| Barındırma | Tek platformda API + worker + Postgres (AB) ve arayüz için Next.js uyumlu AB bölgesi | Kurulum kolaylığı, maliyet, AB, yedekleme | Alfa öncesi (~Hafta 9) |
| İzinli kelime listesi kaynağı | EVP (lisans uygunsa) ya da açık frekans listesi + kendi havuzumuz | Lisans | Faz 0 / Hafta 1–2 |
| Proje adı / alan adı | — | — | Barındırmadan önce |

## 11. Teknik yapım sırası (ilk adımlar)

Blueprint'teki ilk üç işle uyumlu:

1. **Hafta 1:** depo iskeleti (web + api), Alembic ile ilk şema (`users`, `items`, `error_tags`, `events`, `activities`, `item_states`, `llm_calls`), Anthropic API anahtarı + harcama limiti, örnek bir oturumla gerçek token maliyetinin ölçülmesi, içerik içe aktarma formatının Işıl'la netleşmesi.
2. **Hafta 2:** scheduler (FSRS) + birim testler, olay yeniden oynatma, magic link girişi, onam ekranı.
3. **Hafta 3–4:** yerleştirme testi (sabit), müfredat ajanı + kural doğrulayıcı, oturum üretimi + doğrulayıcı, gece işi.
4. **Hafta 5–6:** yazma geri bildirimi + hata etiketleri + altın set betiği (Kapı 2 hazırlığı).
5. Sonrası: TTS/dinleme, panel ve "Ek çalışma", haftalık rapor, yazılı diyalog (esnek), duman testi, barındırma, alfa.

Her hafta sonu Işıl demosu; kararlar `MD files/` altında tek satırlık karar kaydına yazılır.
