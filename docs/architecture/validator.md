# Doğrulayıcı

`app/validator/`: deterministik, LLM'siz. Sonuç `{"version", "ok", "issues": [{"code", "detail"}]}` biçimindedir ve `activity_contents` ile `feedbacks` üzerinde saklanır.

**"Doğrulayıcıdan geçti" "doğru" demek değildir.** Yapıyı ve kelime düzeyini denetler. Şunları yakalayamaz: iki şıkkın da doğru olması, doğal olmayan cümle, seviye dışı dilbilgisi, yanlış Türkçe çeviri (DZ-8). Doğruluk Işıl'ın incelemesiyle ölçülür.

## Kontroller

| Alan | Kodlar |
| --- | --- |
| Etkinlik | `out_of_level`, `target_missing`, `answer_leak`, `duplicate_options`, `answer_not_unique`, `length`, `option_count`, `meaning_too_long`, `missing_task_tr` |
| Geri bildirim | `inconsistent`, `missing_hint`, `missing_correction`, `unknown_code`, `quote_not_found`, `hint_too_long`, `answer_leak`, `no_change`, `over_rewrite`, `out_of_level` |
| Müfredat | `weeks`, `unknown_items`, `repeated_items`, `too_many_items`, `missing_focus`, `missing_can_do`, `english_jargon`, `low_coverage` |
| Ses | `audio_mismatch`; üretilen ses için ayrıca [denetim kapısı](llm.md#ses) |

Seviye sözlüğü `vocab_allowlist` (A1 ve A2) ve öğe biçimlerinden kurulur; düzenli ekler ayrıca çözülür. Liste kaynağı: [ADR-0004](../decisions/0004-seviye-listesi-cefr-j.md).

Geri bildirim için: etiket katalogda, ipucu en fazla 120 karakter ve düzeltme kelimesini içermez, düzeltme öğrencinin cümlesine en az 0,5 benzer ve seviye içindedir, gösterilen hata en fazla 2'dir.

## Hata yeri sunucuda bulunur

Model hata yerini karakter konumu olarak verince kaydırabiliyordu ve doğrulayıcı yalnızca sınırları denetleyebiliyordu. Bu yüzden şema konum istemez: model hatalı kelimeleri alıntılar (`quote`) ve eksik kelimede boşluğun alıntının önünde mi arkasında mı olduğunu söyler (`gap`: none, before, after). Konumu sunucu bulur (`validator/feedback.py: span_of`): kelime sınırında, büyük küçük harf ve boşluk farkı gözetmeden, ilk geçtiği yer. Alıntı metinde yoksa geri bildirim reddedilir (`quote_not_found`). Aynı kelime birden çok geçiyorsa model iki üç kelime alıntılar.

## Bilinen sınırlar

- Cümle başındaki özel isim sıradan kelimeden ayırt edilemez; üretici kullandığı isimleri izinli kelime olarak verir.
- Yazma görevleri seviye kontrolünden geçmiyor.
- Şablon sorular doğrulayıcıdan geçmez; içerik küratörlü alanlardan kurulur, dört şık kurulurken garanti edilir.
- Rakamlar `words()` tarafından atılır.
- `is_correct = true` ve hatasız sonuç kontrolleri atlar: enjeksiyona karşı koruma prompt ve sınırlayıcıya dayanır, [ölçüm](../experiments/2026-11-05-enjeksiyon.md).
