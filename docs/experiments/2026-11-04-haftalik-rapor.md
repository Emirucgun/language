# Deney: Haftalık rapor ve yeniden plan

Tarih: 2026-11-04 · Commit: `15677c1`, düzeltme `67c91da` · Model: Sonnet 5.5 · Prompt: `curriculum/v1`, sonra `curriculum/v2`

## Soru ve hipotez

Yeniden plan somut ve doğru dille açıklanıyor mu?

## Kurulum ve veri

Geliştirme verisiyle bir kullanıcı ve hafta; prompt düzeltmesinden sonra aynı kullanıcı ve hafta.

## Sonuç

**v1:** 8,2 sn, tek Sonnet çağrısı; değişiklik açıklaması somut ve hatalara dayalı. İki ifade sorunu: rapor pazar günü aynı hafta için üretildiği hâlde "geçen hafta" dedi; "artikel" yerine İngilizce "article" kullandı.

**v2:** Türkçe metinde İngilizce dilbilgisi terimi yasak (kural katmanı da `english_jargon` ile reddeder), yeniden planda "bu hafta" dili, ilk cümlede değişikliğin sayıya dayalı nedeni. Sonuç: "Bu hafta tekrar başarın 0,57 olduğu için planı yavaşlattım ve artikel (a/an/the) çalışmasını artırdım." İlk denemede kurallardan geçti, 15 sn, yaklaşık $0.03.

## Karar ve sonraki adım

`curriculum/v2` kaldı.
