# Test

## Bugün

- **Birim ve entegrasyon (pytest):** tekrar motoru, olay yeniden oynatma eşitliği, müfredat kuralları, doğrulayıcı, günlük limit, prompt'ta kişisel veri olmaması, içe aktarma, inceleme kuyruğu, HTTP akışları. Veritabanı testleri `teacher_test` kullanır.
- **LLM:** testler gerçek API'ye gitmez. Sahte istemciler `LLMClient` düzeyindedir (`tests/fakes.py`). Adaptör ise gerçek SDK ile, yalnızca ağı sahteleyerek sınanır (`tests/test_llm_adapter.py`): sahte istemci SDK'nın davranışını gösteremez.
- **Statik:** ruff, mypy (strict, `app/` için), ESLint, `tsc`.
- **CI (`.github/workflows/ci.yml`):** pull request ve `main`'e push'ta `api` (Postgres servisiyle ruff, mypy, pytest), `web` (lint, typecheck) ve `changelog` işleri. Atlanan test varsa `api` kırılır.

## Henüz yok

- Web testi: Vitest ve Playwright kurulu değil (EK-15).
- `next build` CI'da çalışmıyor.
- Altın setin kendisi: araç hazır, etiketli cümleler Işıl'dan gelecek.

## Altın set

`api/eval/`: `golden.py` (çalıştırma), `scoring.py` (API'den bağımsız puanlama), `stats.py` (güven sınırı). Veri `eval/golden/feedback.jsonl`, `scripts.import_golden` ile gelir.

```bash
uv run python -m eval.golden --purpose feedback           # yalnızca dev
uv run python -m eval.golden --purpose feedback --final   # dev ve test, ayrı ayrı
```

Gerçek API çağrısı yapar, ücretlidir, veritabanına iz bırakmaz. CI çalıştırmaz; `--final` CI'da reddedilir. Üretimdeki prompt ve doğrulayıcıyı kullanır, öğrenci özeti vermez.

**Bölme.** Prompt ayarlanırken yalnızca `dev` koşulur. `test` yalnızca nihai ölçüm içindir: ayar sırasında görülen cümle ölçümü geçersiz kılar. `test`teki bir cümle `dev`e alınamaz.

**Ölçütler.** Etiket doğruluğu (gösterilen en fazla 2 etiketten biri eşleşirse doğru), kaçırılan hata, aşırı düzeltme, cevabı ele verme, kabul dışı düzeltme, seviye dışı düzeltme, gösterilemedi; enjeksiyon satırları ayrı sayılır.

**"Kabul dışı düzeltme" yanlış öğretme değildir:** listede olmayan düzeltme doğru da olabilir, bu sayı inceleme adayıdır. Yanlış öğretme insan kararıdır.

## H4 eşiği

H4, `reviews` tablosunda `source = sample` kayıtlarından hesaplanır. Oran değil, tek yönlü %95 Clopper-Pearson üst sınırı kullanılır: 100 yargıda sıfır hata bile %2 kanıtlayamaz. X seçilirken:

| Yargı | 0 hata | 1 hata | 2 hata | 3 hata | 5 hata |
| --- | --- | --- | --- | --- | --- |
| 100 | %3,0 | %4,7 | %6,2 | %7,6 | %10,2 |
| 150 | %2,0 | %3,1 | %4,1 | %5,1 | %6,9 |
| 200 | %1,5 | %2,3 | %3,1 | %3,8 | %5,2 |
| 300 | %1,0 | %1,6 | %2,1 | %2,6 | %3,5 |
| 500 | %0,6 | %0,9 | %1,3 | %1,5 | %2,1 |

Raporda `--h4-limit 0.05` eşiği uygular; karar üst sınıra göre verilir, orana göre değil.

## Kurallar

- `TEST_DATABASE_URL` yoksa veritabanı testleri atlanır; yerelde test sayısına bakın.
- Testler `teacher_test`'i sıfırlar: aynı anda iki yerden koşmayın.
- Gerçek API çağrısı yapan betikler (`try_feedback`, `try_tts`) test değildir; sonuçları [deney kaydı](../experiments/README.md) olur.
