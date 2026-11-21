# ADR-0006: LLM sağlayıcısı olarak Claude

Tarih: 2026-11-03 · Durum: kabul edildi (OA-5'te yeniden değerlendirilecek)

## Bağlam
Elde bulut ya da AI kredisi yok. Pilotta LLM işleminin AB içinde olması şart değil: uygulama ve veritabanı AB'de kalır, Anthropic'in standart DPA ve SCC'si ile ad ve e-posta gönderilmeden çalışılır.

## Karar
Anthropic Claude API doğrudan kullanılır: etkinlik üretimi Haiku 5.5, geri bildirim, diyalog ve müfredat Sonnet 5.5.

## Alternatifler
- Her şey Haiku: yaklaşık $16, ama "yanlış öğretme %2'nin altı" en hassas hedef; Türkçe açıklama kalitesi belirleyici.
- Her şey Sonnet: yaklaşık $324, üretimde gerekmiyor; üretim deterministik doğrulayıcının arkasında.
- Gemini Flash: yaklaşık $122 ve $243; [maliyet modeli](../experiments/2026-11-03-maliyet-modeli.md).
- Vertex AI ya da Bedrock AB uç noktaları: bölgesel ek ücret, kredi yok.

## Sonuçlar
Pydantic şemasıyla yapılandırılmış çıktı yığına doğrudan oturuyor, iki kademe tek SDK ile bir ayar. Erişim için satış onayı gerekmedi.

Yeniden değerlendirme: altın sette Sonnet eşiği tutturamazsa alternatif aynı setle karşılaştırılır; pilot öncesi AB şartı çıkarsa Vertex AI `eu` uç noktasına geçilir. OpenAI'ye geçiş önerisi OA-5 ile ölçülecek; sonucu yeni ADR olur, bu kayıt silinmez.
