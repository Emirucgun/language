# ADR-0004: Seviye listesi olarak CEFR-J

Tarih: 2026-11-03 · Durum: kabul edildi

## Bağlam
Doğrulayıcının seviye dışı kelimeyi yakalaması için lisansı temiz bir liste gerekiyor. Küçük geliştirme listesi çok ret üretiyordu: [ölçüm](../experiments/2026-11-03-gece-uretimi.md).

## Karar
CEFR-J Wordlist Version 1.6 kullanılır (Tono Laboratuvarı, Tokyo Yabancı Diller Üniversitesi); doğrulayıcı A1 ve A2'yi kullanır.

## Alternatifler
- English Vocabulary Profile: ticari kullanım yazılı izin gerektiriyor.

## Sonuçlar
Resmi sayfaya göre atıfla araştırma ve ticari kullanım ücretsiz, türetilmiş liste serbest. İçe aktarma `scripts/import_cefrj.py`: 7.035 kelime (A1 1.088, A2 1.272, B1 2.178, B2 2.497), kelime başına en düşük seviye; düzensiz biçimler lemminflect (MIT) ile üretilir. Yeniden dağıtım açıkça düzenlenmediği için kaynak dosya depoya konmaz; atıf README'de durur.
