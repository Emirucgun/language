# Deney: eval.golden uçtan uca deneme

Tarih: 2026-11-05 · Commit: `ba1c66f` üzerine (Part 7) · Model: Sonnet 5.5 · Prompt: `feedback/v2`

**Bu bir kalite ölçümü değildir.** Etiketler Işıl'ın değil, 11 cümle hiçbir şeyi kanıtlamaz. Amaç aracın gerçek API ile çalıştığını görmekti.

## Soru ve hipotez

`eval.golden` üretimdeki yolla (aynı prompt, aynı doğrulayıcı) çalışıp ayrı bölmeli rapor veriyor mu?

## Kurulum ve veri

`try_feedback` cümlelerinden 10 normal ve 1 enjeksiyon satırı, hepsi `dev`; görev sütunu boş. Etiketleri geçici olarak Emir'in aracı yazdı. Veritabanı `teacher_test`, CEFR-J yüklü. Öğrenci özeti verilmedi: üretimde vardır.

## Sonuç

İki koşu; tek fark varsayılan görev metni.

| Ölçüt | "Write one sentence about yourself." | "Write one short sentence." |
| --- | --- | --- |
| Etiket doğruluğu | 8/8 | 7/8 |
| Kaçırılan hata | 0/8 | 0/8 |
| Aşırı düzeltme | 0/2 | 0/2 |
| Cevabı ele verme | 0/8 | 0/8 |
| Kabul dışı düzeltme | 2/8 | 0/8 |
| Gösterilemedi | 1/10 | 0/10 |
| Enjeksiyonla kandırıldı | 0/1 | 0/1 |
| Maliyet | $0.0245 | $0.0153 |

Medyan gecikme yaklaşık 1,6 sn. Güven sınırları çok geniş: 8 örnekte 0 hata bile "en çok %31,2" demek; 1 enjeksiyon örneği için "en çok %95".

**Bulgular**

- Görev metni düzeltmeyi yönlendiriyor: "about yourself" görevinde `She teacher.` → "I am a teacher.", `Is very nice.` → "I am very nice." Araçtaki varsayılan bu yüzden tarafsız yapıldı.
- İkinci koşudaki tek etiket farkı (`I am eat…`: BE_VERB, beklenen TENSE) büyük olasılıkla geçici etiketin hatası.
- Enjeksiyon satırı modeli kandırmadı; tek örnekten sonuç çıkmaz (DZ-10).

**Güven sınırı.** `eval/stats.py`, `scipy.stats.beta` ile n = 10–500 arasında tüm k değerleri için karşılaştırıldı: en büyük fark 8×10⁻¹⁵.

## Karar ve sonraki adım

Araç hazır. Gerçek ölçüm Işıl'ın dev setiyle. Altın sette **Görev sütunu doldurulmalı**: öğrencinin neye cevap verdiği düzeltmeyi etkiliyor. Sonuç öğrenci özeti olmadan alındı; OA-5'te iki sağlayıcı da aynı koşulda ölçülür.
