# Deney: OpenAI adaptörü, şemalar ve önbellek

Tarih: 2026-11-05 · Commit: `3dc4406` üzerine (Part 8) · Model: `gpt-6.1-sol`, `gpt-6-luna`, `gpt-6.1-terra` · Prompt: `feedback/v2`, `dialogue/v2`, `session/v2`, `curriculum/v2`

**Bu bir sağlayıcı karşılaştırması değildir.** Karşılaştırma OA-5'te Işıl'ın setiyle yapılır.

## Soru ve hipotez

Dört çıktı şeması strict modda geçiyor mu? Kesilme çökmeden yedek yola düşüyor mu? Önbellek üretim koşullarında tutuyor mu?

## Kurulum ve veri

Üretimdeki prompt'lar, kısa görevlerle gerçek API. Önbellek üç durumda ölçüldü: aynı istek; görev farklı; hem görev hem öğrenci özeti farklı. Toplam maliyet yaklaşık $0.10.

## Sonuç

**Şemalar.** `WritingFeedback`, `DialogueTurn`, `SessionOutput`, `CurriculumDraft` gerçek API'den geçti ve ayrıştırıldı. Sol ve Luna ile dört amaç, Terra ile geri bildirim denendi.

**Kesilme.** `max_output_tokens = 40` ile `stop_reason = max_tokens`, `parsed = None`, maliyet kayıtta. Gerçek ret üretilemedi; ret davranışı sahte ağla sınandı.

**Önbellek: asıl bulgu.** Çağrı başına okunan token:

| Amaç | Görev farklı, özet aynı | Özet ayrı `developer` mesajı, özet farklı | Özet `user` mesajında, özet farklı |
| --- | --- | --- | --- |
| Geri bildirim | 1.212 | **0** | 1.193 |
| Diyalog | 1.177 | **0** | 1.158 |
| Oturum | 1.341 | **0** | 1.322 |
| Müfredat | 1.203 | **0** | 1.184 |

Aynı istek tekrarlanınca önbellek kusursuz görünüyordu; farklı öğrenciler hiç paylaşmıyordu. Özet `user` mesajının başına taşınınca sorun kalktı. Sebep kesin bilinmiyor: `developer` mesajının öneki nasıl etkilediği belgede yok. Statik bloklar 1.024 token eşiğini zaten aşıyor, prompt değiştirmek gerekmedi.

Etkisi (Sol, geri bildirim): tam yazma yaklaşık $0.0031, okuma yaklaşık $0.0001.

**Token sayımı farklı.** Aynı geri bildirim prompt'u OpenAI'de yaklaşık 1.240, Claude'da yaklaşık 2.000 token. Liste fiyatları eşit olsa da maliyet aynı değildir; OA-5'te ölçülür.

**Uçtan uca.** `LLM_PROVIDER_FEEDBACK=openai` ile `eval.golden`, geçici etiketli 11 cümle: gösterilemeyen 0, maliyet $0.0130, medyan gecikme 2,2 sn. Tek kabul dışı düzeltme ("I am eating bread and cheese.") geçerli bir alternatif.

## Karar ve sonraki adım

Özet `user` mesajında kalır. Önbellek süresi varsayılan 30 dakika: 12 saatin yazması iki kat pahalı, kazancı en kötü durumda pilot boyunca birkaç dolar; OA-5 verisiyle yeniden bakılır. Sağlayıcı kararı OA-5'te.
