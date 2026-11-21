# Deney: Oturum üretimi ilk ölçüm

Tarih: 2026-11-03 · Commit: `a2052a2` · Model: Haiku 5.5 · Prompt: `session` (sürüm belgede yazmıyor; v1 ya da v2)

## Soru ve hipotez

Bir oturum ne kadara ve ne sürede üretiliyor?

## Kurulum ve veri

Geliştirme içeriği (10 öğe, küçük kelime listesi); istek anında üretim.

## Sonuç

- Oturum başı yaklaşık $0.003 (2 Haiku çağrısı; ikincisi önbellekten 2.958 token okudu).
- Süre yaklaşık 23 sn.
- Reddedilen 5 çıktının hepsi seviye kontrolündendi. Çekim kuralları (`friends→friend`, `watching→watch`) eklendi, kelime listesi genişletildi; aynı 5 çıktı yeniden doğrulamada geçti.

## Karar ve sonraki adım

23 sn beklenemez: gece ön üretimi pilot öncesi şart. Seviye listesi açık karar olarak kaldı (sonra: [ADR-0004](../decisions/0004-seviye-listesi-cefr-j.md)).
