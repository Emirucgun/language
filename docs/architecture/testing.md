# Test

## Bugün

- **Birim ve entegrasyon (pytest):** tekrar motoru, olay yeniden oynatma eşitliği, müfredat kuralları, doğrulayıcı, günlük limit, prompt'ta kişisel veri olmaması, içe aktarma, inceleme kuyruğu, HTTP akışları. Veritabanı testleri `teacher_test` kullanır.
- **LLM:** testler gerçek API'ye gitmez. Sahte istemciler `LLMClient` düzeyindedir (`tests/fakes.py`). Adaptör ise gerçek SDK ile, yalnızca ağı sahteleyerek sınanır (`tests/test_llm_adapter.py`): sahte istemci SDK'nın davranışını gösteremez.
- **Statik:** ruff, mypy (strict, `app/` için), ESLint, `tsc`.
- **CI (`.github/workflows/ci.yml`):** pull request ve `main`'e push'ta `api` (Postgres servisiyle ruff, mypy, pytest), `web` (lint, typecheck) ve `changelog` işleri. Atlanan test varsa `api` kırılır.

## Henüz yok

- Web testi: Vitest ve Playwright kurulu değil (EK-15).
- `next build` CI'da çalışmıyor.
- Altın set ve `eval.golden` (DZ-1, DZ-2).

## Kurallar

- `TEST_DATABASE_URL` yoksa veritabanı testleri atlanır; yerelde test sayısına bakın.
- Testler `teacher_test`'i sıfırlar: aynı anda iki yerden koşmayın.
- Gerçek API çağrısı yapan betikler (`try_feedback`, `try_tts`) test değildir; sonuçları [deney kaydı](../experiments/README.md) olur.
