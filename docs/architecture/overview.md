# Genel bakış

Ürün belgesi **ne** ve **neden**; bu belgeler **nasıl** sorusunu cevaplar. Çelişkide ürün belgesinin hipotezleri (H1–H7) ve kapsam kuralı geçerlidir.

## Yığın

| Katman | Seçim | Not |
| --- | --- | --- |
| Arayüz | Next.js (App Router), TypeScript, Tailwind CSS | Yalnızca arayüz; iş mantığı Next route handler'larında yazılmaz |
| API | Python 3.14, FastAPI, Pydantic v2 | Neden: [ADR-0002](../decisions/0002-python-fastapi.md) |
| ORM ve göç | SQLAlchemy 2, Alembic, psycopg 3 | |
| Veritabanı | PostgreSQL 18 | Tek veritabanı, iki şema: [ADR-0003](../decisions/0003-tek-postgres-iki-sema.md) |
| Arka plan işleri | procrastinate | Postgres tabanlı kuyruk; Redis gerekmez. Bkz. [jobs.md](jobs.md) |
| Tekrar motoru | py-fsrs | `scheduler` modülünün arkasında sarmalı. Bkz. [scheduler.md](scheduler.md) |
| Kimlik | Kendi magic link akışımız ve davet kodu | Bkz. [security-privacy.md](security-privacy.md) |
| LLM | Anthropic Claude; OpenAI adaptörü hazır, ayarla açılır. `LLMClient` arkasında | Bkz. [llm.md](llm.md), [ADR-0006](../decisions/0006-llm-saglayici-claude.md) |
| Ses | `gpt-realtime-2.1-mini`, `TTSClient` arkasında | Sunucu tarafı hazır, arayüz yok. Bkz. [llm.md](llm.md#ses) |
| E-posta | Brevo SMTP | [ADR-0005](../decisions/0005-eposta-brevo.md) |
| Paket yönetimi | Python: uv, Node: npm | |
| Kalite | ruff, mypy, pytest, ESLint, `tsc` | Bkz. [testing.md](testing.md) |
| Loglama | structlog | İki modülde kullanılıyor, henüz yapılandırılmadı (GL-5) |

Henüz yok: nesne deposu (GL-3), hata izleme (GL-5), PWA (EK-15).

**İki dil.** Tek kişilik projede iki dil ek yüktür; bunu azaltmak için arayüz yalnızca API'yi çağırır, tipler OpenAPI şemasından üretilir (`npm run gen:api`) ve Next.js `rewrites` ile `/api/*` isteklerini FastAPI'ye yönlendirir. Tarayıcı tek origin görür: CORS yok, oturum çerezi basit kalır.

## Depo

```
/
├─ web/            Next.js arayüzü
├─ api/
│  ├─ app/
│  │  ├─ auth/          magic link, oturum, davet kodu
│  │  ├─ onboarding/    onam, hedef, yerleştirme testi
│  │  ├─ content/       öğe havuzu ve hata etiketi modelleri
│  │  ├─ curriculum/    müfredat ajanı ve kural doğrulaması
│  │  ├─ scheduler/     FSRS sarmalayıcı, öğe seçimi, günlük kota
│  │  ├─ sessions/      bugünün oturumu, ek çalışma, etkinlik üretimi
│  │  ├─ feedback/      yazma geri bildirimi
│  │  ├─ dialogue/      yazılı diyalog
│  │  ├─ validator/     deterministik doğrulama
│  │  ├─ events/        olay kaydı (yalnızca ekleme)
│  │  ├─ reports/       haftalık rapor ve yeniden plan
│  │  ├─ review/        Işıl'ın inceleme kuyruğu
│  │  ├─ llm/           LLMClient, amaç ayarları, prompt dosyaları
│  │  └─ tts/           TTSClient, denetimli ses üretimi
│  ├─ migrations/   Alembic
│  ├─ scripts/      içe aktarma ve deneme betikleri
│  └─ tests/
├─ content/        tablo şablonları (`templates/`); lisanslı kaynaklar depoya girmez
├─ eval/           altın set ve analiz not defterleri
├─ docs/           teknik belgeler
└─ MD files/       ürün belgesi ve iş listesi
```

## Katmanlar

```
[Next.js] --/api--> [FastAPI]
                      ├─ Kural katmanı: scheduler, curriculum/rules, validator, reports
                      ├─ LLM katmanı:   llm (müfredat, etkinlik, geri bildirim, diyalog)
                      └─ Kayıt:         events (yalnızca ekleme) → türev tablolar
[procrastinate worker] -- oturum ön üretimi, haftalık rapor, geri bildirim yeniden denemesi
[PostgreSQL] -- içerik + olaylar + türev durum + iş kuyruğu
```

## Değişmez kurallar

1. LLM türev tabloya yazmaz. LLM çıktısı → doğrulayıcı → olay ya da etkinlik kaydı → türev durum yalnızca olaylardan hesaplanır.
2. `events` yalnızca eklenir: uygulama rolünün `UPDATE` ve `DELETE` yetkisi yoktur. Bu veritabanı yetkisiyle zorlanır.
3. `item_states` her an olaylardan yeniden hesaplanabilir. Bir test "artımlı güncelleme = baştan yeniden oynatma" eşitliğini doğrular.
4. Hangi öğenin çalışılacağına yalnızca `scheduler` karar verir; etkinlik üretimi bu listeyi girdi olarak alır.
5. Prompt sürümü ve doğrulayıcı sonucu her üretimle saklanır. Model adı `llm_calls`'ta durur; `activity_contents.model` yalnızca `llm` ya da boş değerini taşır.

Uygulama akışları: [flows.md](flows.md).
