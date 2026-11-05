# ADR-0005: E-posta için Brevo

Tarih: 2026-11-04 · Durum: kabul edildi

## Bağlam
Magic link için işlemsel e-posta zorunlu; AB'de işleme tercih ediliyor.

## Karar
Brevo kullanılır (Fransa, AB'de işleme, günde 300 ücretsiz); kod yalnızca SMTP konuşur, sağlayıcı bir ayardır (`app/auth/email.py`).

## Alternatifler
Sağlayıcıya özel API istemcisi: SMTP sağlayıcı değiştirmeyi kod değişikliği olmaktan çıkarır.

## Sonuçlar
Gönderim için alan adı ve SPF, DKIM ayarları gerekir; olmadan e-postalar spam'e düşer. Proje adı kararına bağlı, alfa öncesi kapanmalı (GL-5).
