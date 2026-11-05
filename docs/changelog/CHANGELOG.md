# Değişiklik günlüğü

Her birleştirmede bir satır, en yenisi üstte. Model ve prompt sürümü değişimleri **[MODEL]** ya da **[PROMPT]** ile işaretlenir.

| Tarih | Değişiklik | İlgili iş |
| --- | --- | --- |
| 2026-11-05 | OpenAI Responses adaptörü ve amaç grubu başına sağlayıcı ayarı; `service.py` sağlayıcıdan bağımsız; `llm_calls.provider` (göç 0005). Varsayılan Claude | OA-2 |
| 2026-11-05 | Strict şema, ret ve kesilme iki adaptörde aynı sözleşmeyle; dört şema gerçek API'den geçti | OA-3 |
| 2026-11-05 | OpenAI önbelleği: özet `user` mesajında, önbellekli token sayımı ve fiyatları düzeltildi | OA-4 |
| 2026-11-05 | Ek çalışma çağrıları `extra` amacıyla kaydediliyor | EK-7 |
| 2026-11-05 | `eval.golden`: altın set raporu, bölmeler ayrı, `test` yalnızca `--final`, CI'da reddedilir | DZ-2 |
| 2026-11-05 | Oranlarla birlikte %95 güven sınırı; H4 tanımı blueprint'te üst sınıra çevrildi, X bekliyor | DZ-1 |
| 2026-11-04 | Teknik MVP belgesi `docs/architecture/` altına bölündü, bayat ve çelişen yerler koda göre düzeltildi; eski belge indeks | DK-2, DZ-12 |
| 2026-11-04 | On ölçüm `docs/experiments/` altına taşındı | DK-5 |
| 2026-11-04 | Geçmiş kararlar ADR-0002 ile ADR-0006 arasına yazıldı; sağlayıcı ve TTS kararları OA-5 sonrası | DK-3 |
| 2026-11-04 | İnceleme ekranı (`/review`): `reviewer` rolü, öncelikli "sorun var" kuyruğu, rastgele örnek, dört karar; göç 0004 | GL-1 |
| 2026-11-04 | "Sorun var" düğmesi tüm etkinlik türlerinde ve hedefli; neden sabit listeden | EK-6 |
| 2026-11-04 | İçerik yazım kılavuzu ve inceleme yönergesi | DK-9 |
| 2026-11-04 | Tüm betiklerde Windows çıktı kodlaması düzeltildi | GL-1 |
| 2026-11-04 | **[MODEL]** `TTSClient` ve Realtime adaptörü (`gpt-realtime-2.1-mini`), `gpt-transcribe` ile denetimli ses üretimi, 120 örneklik deney | OA-6 |
| 2026-11-04 | Yeni ses tanıma kuralı ayarda ve kurallarda: yalnızca `gpt-transcribe` | OA-7 |
| 2026-11-04 | ADR-0001: OpenAI hesabı ve işleme bölgesi (önerildi) | OA-1 |
| 2026-11-04 | Yarım yanıt ve ret artık çökmüyor: adaptör `create` ile çağırıp kendisi doğrular, başarısız çağrının maliyeti de kaydedilir | OA-3 |
| 2026-11-04 | E-posta içeren metin ve ilgi alanı istekte reddedilir, hiçbir şey saklanmaz; LLM kapısı artık istisna fırlatmaz | EK-2 |
| 2026-11-04 | Yerleştirme testi bitmeden gece üretimi yapılmaz | EK-3 |
| 2026-11-04 | Yol haritasında hafta numarası yeniden planda sıfırlanmıyor | EK-4 |
| 2026-11-04 | Serbest yazma görevi müfredat sırasını izliyor | EK-5 |
| 2026-11-04 | Günlük kota tek tanımda (`scheduler/quotas.py`); 200 öğeli kapasite testleri; blueprint düzeltildi | DZ-6 |
| 2026-11-04 | Yerel gün sonu vade kesimi testi | DZ-7 |
| 2026-11-04 | Işıl'ın dört tablosu (`content/templates/`) ve satır bazlı raporlu içe aktarma betikleri | GL-2, GL-1 |
| 2026-11-04 | `docs/` iskeleti, durum tablosu, ADR ve deney şablonları | DK-1 |
| 2026-11-04 | Kök `AGENTS.md` ve onu yükleyen `CLAUDE.md` | DK-8 |
| 2026-11-04 | Değişiklik günlüğü başladı | DK-4 |
| 2026-11-04 | GitHub Actions: API testleri, ruff, mypy, web lint ve typecheck, changelog uyarısı | EK-1 |
| 2026-11-04 | `npm run typecheck` temiz klonda çalışıyor (`next typegen`); yerleştirme testindeki rastgele kırılma giderildi | EK-1 |
| 2026-11-04 | Düzeltme ve Geliştirme Listesi depoya alındı; EK işleri ve uygulama partları eklendi | DK-4 |
