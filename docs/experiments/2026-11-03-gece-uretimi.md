# Deney: Gece ön üretimi ve CEFR-J etkisi

Tarih: 2026-11-03 · Commit: `248efc5`, CEFR-J tekrarı `8f789b8` · Model: Haiku 5.5 · Prompt: `session` (sürüm belgede yazmıyor)

## Soru ve hipotez

Arka plan üretimi çalışıyor mu, gerçek seviye listesi ret oranını düşürüyor mu?

## Kurulum ve veri

Yeni kullanıcı için arka plan işi. Sonra aynı profil (seyahat, yemek ve müzik) CEFR-J ile tekrar.

## Sonuç

**Küçük liste:** oturum arka planda 16,6 sn'de üretildi (2 Haiku çağrısı), öğrenci beklemedi. Ama oturum zayıftı: 4 etkinlik, 2'si şablon, okuma yok. Reddedilen 7 çıktının hepsi seviye kontrolündendi (cat, near, museum, flat, things...).

**CEFR-J:** tek Haiku çağrısı, 10,9 sn, $0.0011, 0 ret; 5 etkinliğin hepsi LLM'den, okuma dahil. Önceki 12 ret yeniden doğrulandı: 9'u geçti, kalan 3'ü gerçekten B1 kelimeler (jazz, spicy, strawberries).

## Karar ve sonraki adım

Ret sebebi modelin kalitesi değil küçük listeydi. CEFR-J kaldı.
