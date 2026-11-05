# Deney: Yazma geri bildirimi ilk ölçüm

Tarih: 2026-11-03 · Commit: `883b41f` · Model: Sonnet 5.5 · Prompt: `feedback/v1` (belgede yazmıyor; çıkarım)

## Soru ve hipotez

Geri bildirim doğru mu, önbellek tutuyor mu, gerçek maliyet ne?

## Kurulum ve veri

`scripts/try_feedback.py`, 10 tipik A1 cümlesi. Hata etiketleri ve açıklamalar taslak, seviye sözlüğü geçiciydi. Altın set değil, elle bakıldı.

## Sonuç

- 10/10 doğrulayıcıdan geçti, hata türleri doğru, 2 doğru cümle doğru kabul edildi (aşırı düzeltme yok).
- Önbellek: ilk çağrı 1.971 token yazdı, sonraki 9 çağrı aynısını okudu; önbelleksiz girdi çağrı başına yaklaşık 40 token.
- Çıktı çoğunlukla 80–100 token (bir çağrıda 401).
- Maliyet: ilk çağrı $0.0088, sonrakiler ortalama yaklaşık $0.0015; toplam $0.023. Tahmindeki çağrı ($0.011) gerçekte yaklaşık 7 kat ucuz.
- Gecikme 1,2–8,1 sn, medyan yaklaşık 2,5 sn.

## Karar ve sonraki adım

Sonnet geri bildirim rotasında kaldı. 10 cümle kalite kanıtı değildir; asıl ölçüm altın setle (DZ-1, DZ-2).
