# ADR-0003: Tek Postgres, iki şema

Tarih: 2026-11-03 · Durum: kabul edildi

## Bağlam
Blueprint iki veri deposu öneriyor: içerik ve öğrenci olayları. Tek kişilik projede her altyapı parçası işletme yüküdür.

## Karar
MVP'de tek PostgreSQL veritabanı içinde iki şema kullanılır: `content` ve `learning`; iş kuyruğu da aynı veritabanındadır (`procrastinate` şeması).

## Alternatifler
- İki ayrı sunucu: pilot ölçeğinde kazanç yok, yedekleme ve bağlantı yükü iki kat.
- Ayrı kuyruk altyapısı: bkz. [ADR-0002](0002-python-fastapi.md).

## Sonuçlar
Ayrım mantıksal kalır ve yetkiyle zorlanır: uygulama rolü `content`i yalnızca okur, `events` üzerinde güncelleme ve silme yapamaz. İçerik sahip rolüyle betiklerle yazılır. Tek veritabanı tek arıza noktasıdır: yedek ve geri yükleme testi şart (GL-5).
