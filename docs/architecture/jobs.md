# Arka plan işleri

procrastinate, kendi `procrastinate` şemasında (göç 0003; bağlantı `search_path` ile görür). Worker elle başlatılır: `uv run python -m app.worker`. Windows'ta psycopg'nin asenkron modu için Selector döngüsü açıkça seçilir.

| Zamanlayıcı | Ne zaman | Kuyruğa koyduğu iş | Ne yapar |
| --- | --- | --- | --- |
| `schedule_sessions` | 15 dakikada bir | `generate_session` | Bugünün oturumunu üretir (`ensure_session`) |
| `schedule_weekly_reviews` | Saatte bir (05. dakika) | `weekly_review` | Yerel pazar 20:00 sonrası haftalık rapor ve yeniden plan |
| `schedule_feedback_retries` | Saatte bir (20. dakika) | `retry_feedback` | Gösterilemeyen geri bildirimi yeniden dener |

Zamanlayıcılar uygun kullanıcıları seçer ve kullanıcı başına tek iş açar (`queueing_lock`). `generate_session` 3 deneme hakkıyla çalışır; tekrar çalışması LLM'e ikinci kez gitmez.

`ensure_session` bir iş değildir: kullanıcı oturumu hazır değilse `GET /api/session/today` isteği aynı yolu çalıştırır (GL-6 bu isteği arka plana alacak).

## Oturum seçim kuralı

`app/sessions/scheduling.py`: 03:00 sabit bir zamanlayıcı değildir; 15 dakikalık yoklama yerel saati 03:00'ü geçmiş kullanıcıları seçer. Böylece gece kaçan kullanıcı ya da gün içinde kaydolan biri de yakalanır. Şartlar: onam, 18+ ve hedef tamam, yerleştirme testi bitmiş, son 7 günde aktif ya da yeni kayıt, bugünün oturumu hazır değil. Uzun süredir gelmeyene para harcanmaz; döndüğünde oturum istek anında üretilir.

## Geri bildirim yeniden denemesi

`app/feedback/retry.py`: en fazla 7 günlük yazı, en fazla 3 deneme. Her deneme yeni bir `feedbacks` satırıdır. Diyalog cümleleri atlanır: canlı konuşmada sonradan düzeltme işe yaramaz.

## Henüz yok

`retention_test_due` (DZ-3), `raw_on_failure` temizliği (EK-14), ses üretimi (GL-3).
