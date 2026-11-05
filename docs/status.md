# Durum

Son güncelleme: 2026-11-05 · Haftalık güncellenir. Kaynak: kod taraması (Part 11).

Durum değerleri: **Hazır**, **Kısmi**, **Yok**. "Kod hazır, onay bekliyor" olan işler listede işaretlenmez.

| Özellik | Durum | Engelleyen | Sorumlu |
| --- | --- | --- | --- |
| E-postayla giriş | Kısmi | Alan adı, SPF ve DKIM (GL-5) | Emir |
| Onam | Kısmi | Metin taslak, silme ucu yok (DZ-11) | Emir |
| Yerleştirme testi | Kısmi | İki formda 24'er soru taslak, Işıl onayı yok | Işıl |
| Müfredat ajanı | Hazır | Gerçek öğe havuzu yok | Işıl |
| Oturum üretimi ve doğrulayıcı | Kısmi | Anlamsal kontrol yok (DZ-8) | Emir |
| Gece ön üretimi | Hazır | | Emir |
| FSRS tekrar motoru | Hazır | Eşlemeler pilot verisiyle kalibre edilecek | Emir |
| Yazma geri bildirimi | Kısmi | Yeniden yazma kapısı (DZ-9) | Emir |
| Bekleyen geri bildirim işi | Hazır | | Emir |
| Ek çalışma | Hazır | | Emir |
| Yazılı diyalog | Kısmi | Düzeltmeler gösterilmiyor (EK-11) | Emir |
| Haftalık rapor ve yeniden plan | Hazır | | Emir |
| Dinleme ve TTS | Kısmi | Sunucu tarafı hazır, Işıl'ın dinlemesi bekleniyor (OA-6); arayüz yok (GL-3) | Işıl, Emir |
| Öğe havuzu | Kısmi | İçe aktarıcı hazır; yalnızca yaklaşık 10 geliştirme öğesi var, içerik Işıl'dan | Işıl |
| Altın set ve `eval.golden` | Kısmi | İçe aktarıcı ve araç hazır; etiketli set Işıl'dan | Işıl |
| İnceleme ekranı | Hazır | Sunucuya çıkınca Işıl kullanabilir (GL-5); yerelde de denenebilir | Işıl |
| Hatırlama testi | Hazır | Örnek cümleli gerçek öğe havuzu | Işıl |
| Ön ve son test | Kısmi | B formu taslak; 40 soru kararı (DZ-4) | Işıl |
| OpenAI geçişi | Kısmi | Adaptör hazır, varsayılan Claude; karar OA-5'te, dev seti Işıl'dan | Işıl, Emir |
| CI | Hazır | | Emir |
| Barındırma, yedek, izleme | Yok | GL-5, GL-7 | Emir |
| PWA ve Playwright | Yok | Yap ya da belgeden çıkar kararı (EK-15) | Emir |

## Açık teknik kararlar

| Karar | Ölçüt | Son tarih |
| --- | --- | --- |
| OpenAI'ye geçiş | OA-5 karşılaştırması | Dev seti gelince |
| TTS kesin onayı | Işıl'ın dinlemesi (OA-6) | GL-3'ten önce |
| Barındırma | Kurulum kolaylığı, maliyet, AB, yedekleme | Alfa öncesi |
| Proje adı ve alan adı, SPF ve DKIM | Geçici alan adıyla başlanabilir | Barındırmadan önce |
| PWA ve Playwright | Yap ya da belgeden çıkar (EK-15) | Part 15 |

## Bu hafta

Şu an: Part 11 bitti, sırada Part 12. Part 10 Işıl'ın dev setini bekliyor. Sıra: [Uygulama partları](../MD%20files/D%C3%BCzeltme%20ve%20Geli%C5%9Ftirme%20Listesi.md#uygulama-partlar%C4%B1).

## Kod hazır, onay bekliyor

| İş | Eksik olan |
| --- | --- |
| DK-8 | Aracın yeni bir işe `AGENTS.md`'den başladığı deneme |
| GL-2 | Şablonların Sheets'e yüklenip Işıl'la paylaşılması (Emir) |
| OA-1 | Harcama limiti teyidi ve satışa soru (Emir); ADR-0001 kabulü |
| OA-6 | Işıl'ın 20 ses örneğini dinleyip onaylaması ve hız seçimi |
| GL-1 | Işıl'ın giriş yapıp 10 örnek incelemesi |
| DK-9 | Işıl'ın kılavuzları okuyup soru işaretlemeden bir örnek incelemesi |
| DZ-1 | H4 eşiği X'in Işıl'la seçilmesi; seçenekler `docs/architecture/testing.md` |
| DZ-4 | Işıl'ın B formunu onaylaması ve form başına 24 mü 40 soru mu kararı |
