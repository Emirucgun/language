# Durum

Son güncelleme: 2026-11-04 · Haftalık güncellenir. Kaynak: kod taraması (commit `8eb2fcb`).

Durum değerleri: **Hazır**, **Kısmi**, **Yok**. "Kod hazır, onay bekliyor" olan işler listede işaretlenmez.

| Özellik | Durum | Engelleyen | Sorumlu |
| --- | --- | --- | --- |
| E-postayla giriş | Kısmi | Alan adı, SPF ve DKIM (GL-5) | Emir |
| Onam | Kısmi | Metin taslak, silme ucu yok (DZ-11) | Emir |
| Yerleştirme testi | Kısmi | 24 soru taslak, Işıl onayı yok | Işıl |
| Müfredat ajanı | Hazır | Gerçek öğe havuzu yok | Işıl |
| Oturum üretimi ve doğrulayıcı | Kısmi | Anlamsal kontrol yok (DZ-8) | Emir |
| Gece ön üretimi | Hazır | | Emir |
| FSRS tekrar motoru | Kısmi | Derece eşlemesi (DZ-5) | Emir |
| Yazma geri bildirimi | Kısmi | Yeniden yazma kapısı (DZ-9) | Emir |
| Bekleyen geri bildirim işi | Hazır | | Emir |
| Ek çalışma | Hazır | EK-7 | Emir |
| Yazılı diyalog | Kısmi | Düzeltmeler gösterilmiyor (EK-11) | Emir |
| Haftalık rapor ve yeniden plan | Hazır | | Emir |
| Dinleme ve TTS | Yok | OA-6, GL-3 | Emir, Işıl |
| Öğe havuzu | Kısmi | İçe aktarıcı hazır; yalnızca yaklaşık 10 geliştirme öğesi var, içerik Işıl'dan | Işıl |
| Altın set ve `eval.golden` | Kısmi | İçe aktarıcı hazır; `eval.golden` yok (DZ-1, DZ-2), set Işıl'dan | Işıl, Emir |
| İnceleme ekranı | Yok | GL-1 | Emir |
| Hatırlama, ön ve son test | Yok | DZ-3, DZ-4 | Emir, Işıl |
| OpenAI geçişi | Yok | OA-1 anahtar; OA-5 dev seti | Emir |
| CI | Kısmi | İlk koşu push sonrası görülecek (EK-1) | Emir |
| Barındırma, yedek, izleme | Yok | GL-5, GL-7 | Emir |
| PWA ve Playwright | Yok | Yap ya da belgeden çıkar kararı (EK-15) | Emir |

## Bu hafta

Şu an: Part 3 (sağlamlık ve küçük kurallar). Sıra: [Uygulama partları](../MD%20files/D%C3%BCzeltme%20ve%20Geli%C5%9Ftirme%20Listesi.md#uygulama-partlar%C4%B1).

## Kod hazır, onay bekliyor

| İş | Eksik olan |
| --- | --- |
| EK-1 | GitHub'da ilk koşunun yeşil olması (push gerekir) |
| DK-8 | Aracın yeni bir işe `AGENTS.md`'den başladığı deneme |
| GL-2 | Şablonların Sheets'e yüklenip Işıl'la paylaşılması (Emir) |
