# ADR-0008: Ölçüm testlerinin tasarımı

Tarih: 2026-11-05 · Durum: kabul edildi (eşikler pilot verisiyle gözden geçirilecek)

## Bağlam
H1 "14 gün sonra hatırlama", H3 "ön ve son test" ister. Öğrenciler farklı öğeleri farklı günlerde öğrendiği için H1 sabit testle ölçülemez. Aynı test H3'te iki kez verilirse alıştırma etkisi artış gibi görünür; iki ayrı form verilirse de formların zorluk farkı artış gibi görünebilir.

## Karar
**H3:** seviye testinin iki paralel formu vardır. Öğrencilerin yarısı A ile başlar, yarısı B ile; son test sekiz hafta sonra diğer formla verilir ve aynı puanlamayı kullanır. Son test seviyeyi değiştirmez.

**H1:** kişiye özel, LLM'siz test. Hedef öğe ilk çalışmasından 14–28 gün sonra girer, son üç günde tekrar edilmişse girmez. Yanına çalışılmamış üç kontrol öğesi eklenir. Soru onaylı örnek cümleden kurulur: Türkçe çeviri, İngilizcede boşluk, dört şık. Her öğe en fazla bir kez test edilir; hafta başına en fazla bir test, 5–12 hedef.

## Alternatifler
| Seçenek | Neden seçilmedi |
| --- | --- |
| Herkese önce A, sonra B | Formların zorluk farkı artıştan ayrılamaz |
| Son testte aynı form | Alıştırma etkisi; liste de yasaklıyor |
| 14 gün boyunca öğeyi tekrardan çıkarmak | Öğrenmeyi ölçüm için bozar |
| Son tekrardan 14 gün sonra ölçmek | FSRS aralıkları yüzünden çoğu öğe haftalarca girmez |
| Kontrol öğesiz test | %70 çıksa bile öğrenci zaten biliyor olabilir |
| Çekimli hâli boşluğa koymak | "goes" yanında yalın çeldiriciler cevabı ele verir |

## Sonuçlar
H1, uygulamanın tekrarlarıyla birlikte kalıcılığı ölçer: tekrarsız bellek değil, ürünün gerçek etkisi. Tabanın üstündeki fark (`net`) asıl sayıdır.

`fixed_tests` satırı artık ön mü son mu olduğunu bilmez; bu olaydaki `phase` alanındadır. `pre`, `post` ve `retention` amaçları kalktı (göç 0006).

Sınırlar: `structure` öğeleri ve örneklerinde yalın hâli geçmeyen öğeler teste giremez; içe aktarıcı ikincisini uyarır. Test öğeyi bir kez daha gösterdiği için kontrol öğesi hafif bir tanışıklık kazanır. Bir öğrencinin cevapları bağımsız olmadığından güven sınırı iyimserdir; öğrenci ortalamasıyla birlikte okunur. Sekiz hafta sınırı takvimlidir: az çalışan öğrenci de son testi alır, analizde ayrılması gerekebilir.
