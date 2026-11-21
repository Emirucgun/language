# ADR-0007: Şıklı cevabın FSRS derecesi

Tarih: 2026-11-05 · Durum: kabul edildi (pilot verisiyle H1'e göre kalibre edilecek)

## Bağlam
Şıklı soruda tahmin şansı var; "doğru → Good" kararlılığı abartıyor (DZ-5). Liste "şıklı doğru → Hard" öneriyordu. Simülasyon bunun zararlı olduğunu gösterdi: FSRS'te Hard öğrenme aşamasından çıkarmaz, her zaman doğru bilen öğrenci bir öğeyi 8 haftada 68 kez tekrar eder. Tekrar kuyruğu dolunca yeni öğe kotası yarıya iner.

## Karar
Şıklı doğru öğrenme aşamasında Good, tekrar aşamasında Hard sayılır; ipuçlu doğru her zaman Hard, ipucusuz yazılı doğru Good, yanlış Again.

## Alternatifler
| Kural | 8 haftada tekrar | Son kararlılık |
| --- | --- | --- |
| Hep Good (eski) | 4 | 46 gün |
| Hep Hard (liste) | 68 | 1,3 gün, öğrenmede takılı |
| **Öğrenmede Good, tekrarda Hard** | 5 | 36 gün |
| Aynısı, her 4. cevap yazılı Good | 5 | 57 gün |

Kaynak: [deney kaydı](../experiments/2026-11-05-derece-eslemesi.md).

## Sonuçlar
Şıklı başarı daha az güven verir, öğe yine ilerler, yazılı üretim belirgin biçimde ödüllendirilir. Derece cevap anında olaya yazıldığı için yeniden oynatma deterministik kalır; eski olaylar değişmez. Hep ipucu kullanan öğrenci öğrenmede takılabilir: pilotta izlenir. Ağırlıklar başlangıç değeridir.
