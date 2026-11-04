# Proje kuralları (yapay zeka aracı için)

A1–A2 seviyesinde Türkçe konuşan yetişkinler için yapay zeka destekli İngilizce özel öğretmen. Emir tek başına kodluyor, öğretim kalitesi Işıl'da. İletişim Türkçe. Araç CTO gibi davranır: seçenek sıralamak yerine karar verir ve kaydeder.

## Başlarken

1. Sıradaki işler ve kimlikler (OA, DZ, GL, DK, EK): `MD files/Düzeltme ve Geliştirme Listesi.md`. İşin kabul ölçütü sağlanmadan kutu işaretlenmez.
2. Durum: `docs/status.md`. Belge düzeni ve kurallar: `docs/README.md`.
3. Mimari: `docs/architecture/`; taşınmamış konular için `MD files/Technical MVP – …md`.
4. Bu belgeler kodu özetler, yerine geçmez. İddiayı kodda doğrula; çelişki bulursan belgeyi düzelt.

## Değişmez kurallar

- `learning.events` yalnızca eklenir: güncelleme ve silme yok. Uygulama rolünün bu yetkisi de yoktur.
- LLM türev tablolara yazmaz. Durum olaylardan türetilir.
- Öğe seçimi yalnızca `api/app/scheduler/` içinde yapılır; LLM hangi öğenin çalışılacağına karar vermez.
- Kişisel veri prompt'a girmez. Tüm LLM çağrıları `app/llm/service.py` üzerinden geçer: limit, koruma ve `llm_calls` kaydı oradadır. Sağlayıcı SDK'sını başka yerden çağırma.
- LLM çıktısı doğrulayıcıdan geçmeden öğrenciye gitmez. "Doğrulayıcıdan geçti" "doğru" demek değildir.
- Hata yerini model değil sunucu bulur: model alıntılar, konumu `span_of` hesaplar.
- İçerik kimlikleri korunur: öğe ve etiket satırı silinmez, pasifleşir; sabit test yeni sürümle değişir.
- Prompt dosyaları değiştirilmez: `app/llm/prompts/<amaç>/vN.md` yeni sürüm olarak eklenir, eskisi kalır.

## Yasaklar

- Sağlayıcı anahtarını, şifreyi ya da `.env` içeriğini koda, belgeye ya da commit'e yazma.
- Model adını ve fiyatını koda sabitleme; ayarda durur.
- Hook atlama (`--no-verify`) ve test silerek ya da atlayarak yeşile geçme.
- `content/sources/` altındaki lisanslı dosyaları depoya ekleme.
- Yeni ses tanıma kodunda `gpt-transcribe` dışında model kullanma; konuşma MVP kapsamı dışındadır.

## Her değişiklikte

Kod değişikliği = kod + test + ilgili belge + `docs/changelog/CHANGELOG.md` satırı, aynı commit'te.

- Önemli karar (model, prompt, sağlayıcı dahil): `docs/decisions/` altında ADR.
- Ölçüm: `docs/experiments/` altında yeni kayıt.
- Model ya da prompt değişikliği: altın set raporu olmadan birleşmez (`eval.golden` Part 7'de geliyor; o zamana kadar elle ölçüp deney kaydı bırak).
- Şema değişikliği: yeni Alembic göçü; `upgrade` ve `downgrade` çalışmalı.
- API değişikliği: `npm run gen:api` ile `web/src/lib/api-types.ts` yenilenir.

## Komutlar

`api/` içinde:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy
uv run alembic upgrade head
uv run python -m scripts.seed_dev_content
uv run python -m app.worker
uv run python -m scripts.export_openapi ../web/openapi.json
uv run python -m scripts.make_templates
```

Işıl'ın tabloları (`--apply` olmadan yalnızca rapor verir; akış: `docs/content/tablolar.md`):

```bash
uv run python -m scripts.import_items dosya.xlsx
uv run python -m scripts.import_error_tags dosya.xlsx
uv run python -m scripts.import_placement dosya.xlsx
uv run python -m scripts.import_golden dosya.xlsx
```

`web/` içinde:

```bash
npm ci
npm run lint
npm run typecheck
npm run gen:api
```

Web testi henüz yok; `web/AGENTS.md` Next.js sürüm uyarısını içerir, web kodundan önce oku.

## Ortam tuzakları

- `TEST_DATABASE_URL` yoksa veritabanı testleri hata vermeden atlanır. Sonuçtaki test sayısına bak: atlama olmamalı.
- Testler `teacher_test` veritabanını sıfırlar; aynı anda iki yerden koşma.
- Makine Windows 10, 6 GB RAM: Docker yok, PostgreSQL servis olarak çalışır, araçlar hafif tutulur.
- Worktree'de `api/.env` ve `node_modules` yoktur; önce kurulum gerekir.
