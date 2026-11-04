# LLM katmanı

Sağlayıcı kararı: [ADR-0006](../decisions/0006-llm-saglayici-claude.md). Maliyet modeli: [deney kaydı](../experiments/2026-11-03-maliyet-modeli.md).

## Tek kapı

Tüm çağrılar `app/llm/service.py` içindeki `generate_structured` üzerinden geçer: günlük limit, kişisel veri koruması, çağrı, `llm_calls` kaydı ve maliyet.

```python
generate_structured(session, client, prompt=Prompt(...), output_type=Model, user_id=...)
    -> (parsed | None, LlmCall)
```

**Hata sözleşmesi.** Ret, kesilme, şema dışı çıktı, API hatası ve kişisel veri istisna fırlatmaz: sonuç `None` döner, çağıran yedek yola geçer ("şimdilik atladık" ya da şablon). Yalnızca günlük limit `DailyLimitExceeded` fırlatır. Başarısız çağrının token kullanımı da kaydedilir.

Çağrı zaman aşımı 60 sn; SDK geçici hataları (429, 5xx, bağlantı) 2 kez yeniden dener.

`LLMClient.complete` yanıt geldiyse istisna fırlatmaz. Bu yüzden adaptör SDK'nın `parse` yardımcısını değil `create` kullanır ve JSON'u `parse_output` ile kendisi doğrular: `parse` şema dışı yanıtta `ValidationError` fırlatıp kullanım bilgisini kaybettirir. Yalnızca `stop_reason == "end_turn"` kabul edilir; kesilmiş JSON tam görünse de güvenilmez.

## Amaç tablosu

`app/llm/purposes.py`; model adları ayardır (`app/config.py`).

| Amaç | Model | `max_tokens` | `effort` | Sunucu tarafı yedek |
| --- | --- | --- | --- | --- |
| `session` | Haiku 5.5 | 8000 | low | Hayır |
| `extra` | Haiku 5.5 | 4000 | low | Hayır |
| `feedback` | Sonnet 5.5 | 2000 | medium | Evet |
| `dialogue` | Sonnet 5.5 | 1500 | low | Evet |
| `curriculum` | Sonnet 5.5 | 8000 | medium | Evet |

`extra` ayarı şu an kullanılmıyor: ek çalışma `session` amacıyla çağrılıyor (EK-7). Kullanıcı başına günlük limit 20 çağrı; başarısız çağrılar da sayılır.

Model API'si notları: `temperature` ve `top_p` gönderilmez, güncel API reddediyor. Düşünme varsayılan olarak açık ve çıktı token'ı olarak faturalanır; `max_tokens` buna dahildir, maliyet `effort` ile yönetilir.

## Prompt sürümleri

Dosyalar `app/llm/prompts/<amaç>/vN.md`. Yeni sürüm yeni dosyadır, eskisi eski `llm_calls` kayıtları için kalır. Sürüm çağıran modülde sabittir (`PROMPT_VERSION`).

| Amaç | Güncel | Son değişiklik |
| --- | --- | --- |
| `session` | v2 | "Can" isim listesinden çıktı (modal "can" ile karışıyordu) |
| `feedback` | v2 | Hata yeri karakter konumu değil alıntı |
| `dialogue` | v2 | Hata yeri karakter konumu değil alıntı |
| `curriculum` | v2 | Türkçe metinde İngilizce dilbilgisi terimi yok; yeniden planda "bu hafta" dili |

Model ya da prompt değişikliği altın set raporu olmadan birleşmez (`eval.golden` henüz yok: DZ-1, DZ-2).

## Bağlam ve önbellek

Hafıza dosyası fikri: kısa bir özet oturum başında sisteme donmuş olarak girer, önek sabit kaldığı için önbellek tutar. Bizde hafızayı LLM yazmaz: özet olaylardan deterministik üretilir.

İstek üç katmanlıdır:

1. **Statik blok:** amaç başına herkes için aynı; rol, kurallar, hata kodu listesi, örnekler. 1 saatlik önbellek.
2. **Öğrenci özeti** (`app/llm/snapshot.py`): en fazla 300 token, günde bir donar. Seviye, hedef, ilgi alanları, zayıf beceri, en sık 3 hata kodu, bugünün odağı. 5 dakikalık önbellek.
3. **Görev:** yalnızca bu görevin girdisi; önbelleğe alınmaz.

Maliyetin büyük kısmı çıktıda olduğu için çıktı da hedeflenir: Türkçe açıklama katalogdan gelir, model yalnızca kod ve kısa ipucu döndürür; şemalar girdiyi yankılamaz; doğrulanmış kısa etkinlikler (hatırlama, yeni öğe) aynı öğe, seviye ve ilgi alanı için yeniden kullanılır. Okuma, diyalog ve geri bildirim kişiye özeldir.

Sıkıştırma gerekmez: çağrılar tek seferlik, tek çok turlu iş olan diyalog 4–6 turla sınırlıdır. Önbellek token'ları `llm_calls`'ta izlenir. Gece üretimi için Batch API sonraki optimizasyondur.

## Oturum tek çağrıda

Tek çağrı tüm oturumu üretir, ama doğrulama etkinlik bazındadır: kalanlar yalnızca kendileri için yeniden üretilir, ikinci kez kalırsa yedek şablona düşer. Ayrıntı: [flows.md](flows.md#etkinlik-üretimi).

## Ses

`app/tts/`: `TTSClient` arayüzü ve Realtime adaptörü (`gpt-realtime-2.1-mini`). Ölçümler: [deney kaydı](../experiments/2026-11-04-tts-realtime.md).

Model sohbet modelidir ve cümleyi okumayabilir. Bu yüzden ses yalnızca `synthesize_checked` ile üretilir: her ses `gpt-transcribe` ile ayrıca dinlenir, geçmezse en çok 3 kez yeniden üretilir. Kapı rakamları göremez: dinleme cümlelerinde sayılar yazıyla yazılır. Hız `audio.output.speed` ile ayarlanır (belgede yok, ölçüldü); talimatla yavaşlatma kullanılmaz.

Yeni ses tanıma kodu yalnızca `gpt-transcribe` kullanır; konuşma MVP kapsamı dışındadır.
