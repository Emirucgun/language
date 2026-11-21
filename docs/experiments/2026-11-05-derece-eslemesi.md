# Deney: Şıklı cevap derecesi ve şık konumu

Tarih: 2026-11-05 · Commit: `fcdcbe5` üzerine (Part 9) · Model: FSRS simülasyonu, geliştirme verisi, `claude-haiku-5-5`, `gpt-6-luna` · Prompt: `session/v3`

## Soru ve hipotez

DZ-5 "şıklı doğru → Hard" diyor. Bu tekrar yükünü nasıl etkiler? Şıklar gerçekten tahmine karşı dengeli mi?

## Kurulum ve veri

- **Derece:** `apply_review` ile tek öğe, 56 gün, öğrenci her zaman doğru bilir ve vadesinde çalışır, günde en fazla bir kez.
- **Konum:** `teacher_dev` içindeki LLM üretimi 30 şıklı soru. Sonra `session/v3` ile iki modelde 12'şer soru.

## Sonuç

**Derece.**

| Kural | Tekrar | İlk aralıklar (gün) | Kararlılık |
| --- | --- | --- | --- |
| Hep Good (eski) | 4 | 0,8 · 2 · 11 · 46 | 46,3 |
| Hep Hard (liste) | 68 | 0,8 · 0,8 · 0,8 · 0,8… | 1,3 |
| Öğrenmede Good, tekrarda Hard | 5 | 0,8 · 2 · 8 · 19 · 36 | 35,8 |
| Aynısı, her 4. cevap yazılı Good | 5 | 0,8 · 2 · 8 · 26 · 57 | 57,1 |

Hep Hard'da öğe öğrenme aşamasından hiç çıkmıyor.

**Konum: asıl bulgu.** Geliştirme verisinde doğru cevap 30 sorunun **29'unda ilk şıktı** ve ekrana bu sırayla gidiyordu. Öğrenci hep ilk şıkkı seçse neredeyse tam puan alırdı; tempo ve hatırlama ölçümleri geçersiz kalırdı.

`session/v3` ile (0 = ilk şık):

| Model | Şık sayısı | Doğru cevabın konumu |
| --- | --- | --- |
| Haiku 5.5 | 12/12 dört şık | 0: 4, 1: 5, 2: 2, 3: 1 |
| Luna | 12/12 dört şık | 0: 2, 1: 5, 2: 5, 3: 0 |

Prompt yardımcı oluyor ama dengelemiyor; bu yüzden sıra sunucuda karıştırılır. Tarayıcıda doğrulandı: saklanan sıradan farklı, yenilemede sabit.

## Karar ve sonraki adım

[ADR-0007](../decisions/0007-sikli-cevap-derecesi.md). Şıklar öğrenciye özgü sabit sırayla karıştırılır (EK-16). Eski 3 şıklı paylaşılan içerik yeniden kullanılabilir; pilot öncesi veritabanında gerçek öğrenci yok, gerçek havuzla sıfırdan üretilir.
