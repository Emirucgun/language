# Proje belgeleri

Her bilgi türü kendi yerinde durur. Bir bilgi tek yerdedir; diğer belgeler ona bağlantı verir.

| Yer | Cevapladığı soru | Ne zaman güncellenir |
| --- | --- | --- |
| [status.md](status.md) | Neler hazır, neyi bekliyor? | Haftalık, 15 dakika |
| [product/](product/README.md) | Ne yapıyoruz, neden? | Ürün kararı değişince |
| [architecture/](architecture/README.md) | Sistem şu an nasıl çalışıyor? | Mimari her değiştiğinde, aynı değişiklikte |
| [decisions/](decisions/README.md) | Neden böyle karar verdik? | Her önemli kararda; eskisi silinmez |
| [changelog/CHANGELOG.md](changelog/CHANGELOG.md) | Ne zaman ne değişti? | Her birleştirmede bir satır |
| [experiments/](experiments/README.md) | Neyi ölçtük, ne çıktı? | Her ölçümde, yeni dosya olarak |
| [runbooks/](runbooks/README.md) | Bir şey bozulunca ne yapacağız? | İlgili altyapı değişince |
| [content/](content/README.md) | İçerik nasıl yazılır ve incelenir? | Kılavuz değişince |
| [reference/](reference/README.md) | Tam alan ve uç nokta listesi | Elle değil, otomatik üretilir |

Sıradaki işlerin listesi: [Düzeltme ve Geliştirme Listesi](../MD%20files/D%C3%BCzeltme%20ve%20Geli%C5%9Ftirme%20Listesi.md). Yapay zeka aracı kuralları: [AGENTS.md](../AGENTS.md).

## Kurallar

1. Bir bilgi tek yerde durur; diğer belgeler ona bağlantı verir.
2. Mimari belgeler güncel durumu anlatır; geçmiş changelog ve deney kayıtlarında kalır.
3. Kod değişikliği aynı birleştirmede ilgili belgeyi, testi ve changelog satırını günceller; changelog satırı eksikse CI uyarır.
4. Her önemli karar tek sayfalık ADR olur; model, prompt ve sağlayıcı değişikliği bu kapsamdadır.
5. Ölçüm yapan her iş deney kaydı bırakır: tarih, commit, model ve prompt sürümü, veri, sonuç, karar.
6. Ürün belgeleri ve depodaki teknik belgeler birbirini bağlantıyla gösterir; çelişkide ürün belgesindeki hipotezler ve kapsam kuralı geçerlidir.
