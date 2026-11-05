# Deney: Pilot maliyet modeli

Tarih: 2026-11-03 · Commit: `883b41f` · Model: Haiku 5.5, Sonnet 5.5 (liste fiyatı) · Prompt: yok (hesap)

## Soru ve hipotez

Pilot metin maliyeti ne kadar ve hangi model karışımı seçilmeli?

## Kurulum ve veri

Tahmin, ölçüm değil. Fiyatlar (milyon token, girdi / çıktı): Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10.

Kullanıcı-gün başına varsayım: oturum üretimi (3k girdi, 5k çıktı), 1 ek çalışma (2,5k, 2,5k), 2 geri bildirim ya da diyalog çağrısı (her biri 1,5k, 0,8k). Düşünme token'ları çıktıya dahil. 50 kullanıcı × 60 gün = 3.000 kullanıcı-gün, yaklaşık 25M girdi ve 27M çıktı token.

## Sonuç

| Senaryo | Pilot toplamı |
| --- | --- |
| Hepsi Haiku 5.5 | ~$16 |
| **Seçilen karışım (üretim Haiku, geri bildirim Sonnet)** | **~$79** |
| Haftalık müfredat (Sonnet), ek olarak | ~$27 |
| Hepsi Sonnet 5.5 | ~$324 |
| Karşılaştırma: Gemini Flash (giriş / 2027 fiyatı) | ~$122 / ~$243 |

Asıl maliyet çıktıda (yaklaşık %75).

## Karar ve sonraki adım

Karışım seçildi: [ADR-0006](../decisions/0006-llm-saglayici-claude.md). Bütçe: geliştirme, altın set koşuları ve pilot dahil $150 üst sınır; konsolda harcama limiti. Gerçek token sayıları `llm_calls`'tan doğrulanır; tahmin %50'den fazla saparsa model güncellenir. OpenAI için OA-5'te yeniden ölçülür.
