# Durum

Son güncelleme: 2026-11-04 · Haftalık güncellenir. Kaynak: kod taraması (commit `8eb2fcb`).

Durum değerleri: **Hazır**, **Kısmi**, **Yok**. "Kod hazır, onay bekliyor" olan işler listede işaretlenmez.

| Özellik | Durum | Engelleyen | Sorumlu |
| --- | --- | --- | --- |
| E-postayla giriş | Kısmi | Alan adı, SPF ve DKIM (GL-5) | Emir |
| Onam | Kısmi | Metin taslak, silme ucu yok (DZ-11) | Emir |
| Yerleştirme testi | Kısmi | 24 soru taslak, Işıl onayı yok; EK-3 | Işıl |
| Müfredat ajanı | Hazır | Gerçek öğe havuzu yok; DZ-6 | Emir |
| Oturum üretimi ve doğrulayıcı | Kısmi | Anlamsal kontrol yok (DZ-8) | Emir |
| Gece ön üretimi | Hazır | | Emir |
| FSRS tekrar motoru | Kısmi | Derece eşlemesi (DZ-5) | Emir |
| Yazma geri bildirimi | Kısmi | Yarım yanıtta yedek yol çalışmıyor (OA-3, EK-2); DZ-9 | Emir |
| Bekleyen geri bildirim işi | Hazır | | Emir |
| Ek çalışma | Hazır | EK-5, EK-7 | Emir |
| Yazılı diyalog | Kısmi | Düzeltmeler gösterilmiyor (EK-11) | Emir |
| Haftalık rapor ve yeniden plan | Kısmi | EK-4 | Emir |
| Dinleme ve TTS | Yok | OA-6, GL-3 | Emir, Işıl |
| Öğe havuzu | Yok | Yalnızca yaklaşık 10 geliştirme öğesi var; içe aktarıcı yok (GL-1, GL-2) | Işıl, Emir |
| Altın set ve `eval.golden` | Yok | DZ-1, DZ-2; set Işıl'dan | Işıl, Emir |
| İnceleme ekranı | Yok | GL-1 | Emir |
| Hatırlama, ön ve son test | Yok | DZ-3, DZ-4 | Emir, Işıl |
| OpenAI geçişi | Yok | OA-1 anahtar; OA-5 dev seti | Emir |
| CI | Kısmi | İlk koşu push sonrası görülecek (EK-1) | Emir |
| Barındırma, yedek, izleme | Yok | GL-5, GL-7 | Emir |
| PWA ve Playwright | Yok | Yap ya da belgeden çıkar kararı (EK-15) | Emir |

## Bu hafta

Şu an: Part 1 (Temel). Sıra: [Uygulama partları](../MD%20files/D%C3%BCzeltme%20ve%20Geli%C5%9Ftirme%20Listesi.md#uygulama-partlar%C4%B1).

## Kod hazır, onay bekliyor

| İş | Eksik olan |
| --- | --- |
| EK-1 | GitHub'da ilk koşunun yeşil olması (push gerekir) |
| DK-8 | Aracın yeni bir işe `AGENTS.md`'den başladığı deneme |
