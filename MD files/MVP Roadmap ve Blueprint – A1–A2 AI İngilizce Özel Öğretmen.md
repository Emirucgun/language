# MVP Roadmap ve Blueprint – A1–A2 AI İngilizce Özel Öğretmen

Nov 3, 2026 · @Emir Ucgun

## 1. MVP'nin amacı ve "bitti" tanımı

MVP, pazar büyüklüğünü ya da ölçeği değil tek bir şeyi kanıtlamak zorunda: **öğrenciyi tanıyan, kural tabanlı tekrar ve Türkçe kaynaklı geri bildirimle çalışan bir sistem, A1–A2 düzeyindeki bir yetişkini 8 hafta boyunca çalıştırıp gözlemlenebilir şekilde ilerletebiliyor mu?** Bu doküman, Notion'daki soru listesi bitmeden başlayıp soruları MVP ile paralel kapatmak için yazıldı: cevapsız bir soru, ilgili bileşeni "varsayım" olarak işaretleyip ilerlememize izin verir (bkz. Bölüm 11).

Ölçütlerin hepsi vizyon dokümanındaki hipotez hedeflerdir; pilot verisi gelmeden kesinleşmiş sayılmaz.

| Hipotez | Nasıl ölçülür | Hedef (doğrulanacak) |
| --- | --- | --- |
| H1. Öğrenilen şey kalıyor | 14 gün sonra kelime ve kalıp hatırlama testi | En az %70 |
| H2. Kullanıcı geri geliyor | 8. haftada haftalık aktif kullanıcı oranı | En az %40 |
| H3. Seviye gerçekten artıyor | Ön test ve son test (A1–A2 kısa yerleştirme testi) | Anlamlı artış |
| H4. Üretilen içerik ve geri bildirim doğru | Işıl'ın rastgele örneklem kontrolü (etkinlik, hata etiketi ve açıklama) | Yanlış öğretme %2'nin altı |
| H5. Türkçe kaynaklı açıklama işe yarıyor | Geri bildirim sonrası "anladım / anlamadım" tıklaması | Açıklamaların çoğunda "anladım" (eşik pilotta belirlenir) |
| H6. Memnuniyet | Pilot sonu NPS | 30 ve üzeri |
| H7. Kişiye özel müfredat ve "Önerilen" etiketi işe yarıyor | Önerilen etkinliği seçme oranı; müfredat görme ile 8. hafta aktifliği ilişkisi (gözlemsel, nedensel iddia yok) | Yön gösterir; eşik pilotta belirlenir |

**Bitti tanımı (pilota çıkış kapısı):**

- Emir ve Işıl 14 gün boyunca ürünü kendileri günlük kullandı ve kritik hata kalmadı.
- 5 kişilik alfa grubu (arkadaş ve aile, A1–A2 düzeyinde) en az 7 gün kullandı.
- Geri bildirim modülünde Işıl'ın kontrol ettiği 100 örnekte yanlış öğretme oranı ölçüldü ve hedefin altında.
- Olay kaydı (Bölüm 5) her etkinlikte eksiksiz yazıyor ve haftalık raporu otomatik üretebiliyor.

## 2. Kapsam

MVP tek bir döngüyü mükemmel yapar: **öğren → tekrar et → yaz → geri bildirim al → sistem seni daha iyi tanır.** Uzun vadeli vizyondaki dört beceriden okuma, yazma ve kelime/kalıp MVP'de, dinleme TTS ile, konuşma ise sonraki fazdadır; etkinlikler kişiye özel canlı üretilir.

| Bileşen | Durum | Not |
| --- | --- | --- |
| Kısa yerleştirme testi (A1 ve A2 alt düzeyleri) | MVP | 10 dakika, kelime + yapı + kısa okuma + kısa dinleme |
| Hedef ve ilgi alanı anketi | MVP | Müfredat ve örneklerin kişiselleşmesi için |
| Müfredat ajanı: hedefe göre \~8 haftalık taslak, haftalık yeniden plan | MVP | Kural katmanı doğrular; vaat değil tahmin gösterilir |
| Öğrenci modeli (öğe bilgisi, hata örüntüleri, tekrar zamanlaması, hedef) | MVP | Bu ürünün çekirdeği |
| Tekrar motoru (FSRS tipi, LLM'den bağımsız) | MVP | Kural tabanlı, test edilebilir |
| Canlı, kişiye özel etkinlik üretimi (hatırlama, yeni öğe, okuma, dinleme, yazma) | MVP | Bugünün oturumu önceden, ek çalışma türleri talep anında üretilir; hepsi doğrulayıcıdan geçer |
| Yazılı diyalog (rol yapma, 4–6 tur) | MVP (esnek) | Hedefi sohbet olanlar için; zaman kalırsa Hafta 11'de |
| Kullanıcı paneli: müfredat, ilerleme, etkinlik türü seçimi, "Önerilen" etiketi | MVP | Sade: "Bugünün oturumu" ana düğme, tür seçimi "Ek çalışma"da; süs yok |
| Yazma geri bildirimi, Türkçe kaynaklı hata etiketli | MVP | Cümle düzeyi, açıklaması Türkçe |
| Türkçe destekli arayüz ve açıklamalar | MVP | A1'de ana dil desteği gerekli (soru L1-8) |
| Seslendirme ile dinleme (TTS) | MVP | Beceriye göre ayarlanan dinleme için gerekli, artık esnek değil |
| Haftalık ilerleme raporu | MVP | Öğrenci modelinden otomatik |
| Mobil uyumlu web uygulaması, e-posta ile giriş | MVP | PWA; yerel uygulama yok |
| Olay ve etkinlik kaydı, temel analitik | MVP | Ölçüm ve denetim için zorunlu |
| Onam ekranı ve sade gizlilik metni (KVKK/GDPR) | MVP | Pilot öncesi zorunlu |
| Konuşma, ses tanıma, telaffuz analizi | Kapsam dışı | Faz 2 (soru BC10) |
| Ödeme, abonelik | Kapsam dışı | Pilot sonrası ücretlendirme testi |
| Oyunlaştırma, avatar, yüksek animasyon | Kapsam dışı | Odak öğrenme, eğlence değil |
| B1 ve üzeri, başka diller, öğretmen paneli, yerel mobil uygulama | Kapsam dışı | Genişleme fazı |

**Kapsam kuralı:** Bir özellik H1–H7 ölçütlerinden birini doğrudan beslemiyorsa MVP'ye girmez.

## 3. Kullanıcı yolculuğu

Yolculuk üç parçadır: hedefe göre kişisel bir **müfredat taslağı**, panelden yönetilen **günlük çalışma** ve her hafta **yeniden planlama**. Etkinliklerin hepsi her kullanıcı için LLM tarafından üretilir; aşağıdaki akış bir ürün özelliğidir, ekran tasarımı değildir.

**İlk gün (yaklaşık 15–20 dakika)**

1. Davet bağlantısı ile giriş, onam ve gizlilik metni.
2. Hedef ve süre soruları: neden İngilizce (seyahat, iş, okul, günlük sohbet), günde kaç dakika, hangi beceriyi eksik hissediyor, ilgi alanları.
3. Kısa yerleştirme testi: kelime, yapı, okuma ve dinleme.
4. Test sonucu ve hedef **müfredat ajanına** gider. Ajan 8 haftalık (süre değişebilir) bir taslak müfredat üretir: haftalık odak, tahmini öğe sayısı ve her hafta sonunda kullanıcının yapabileceği şeyler. Kural katmanı taslağı öğe havuzuna ve CEFR seviyesine karşı doğrular.
5. Kullanıcı müfredatı bir kitabın içindekiler bölümü gibi görür. Süre ve seviye **aralık ve tahmin** olarak gösterilir, söz olarak değil: günde 10–15 dakika ile 2 ayda tam bir CEFR seviyesi atlamak gerçekçi olmayabilir (soru SK6 açık).

**Panel**

- **Ana düğme: "Bugünün oturumu".** Kullanıcı gelmeden önce hazırlanır, bekleme yoktur. İçeriği (hangi öğeler, hangi beceri ağırlığı) kural katmanı belirler; panelde "Önerilen" etiketi bunun üzerindedir.
- **"Ek çalışma" bölümü:** tekrar, okuma, dinleme, yazma, yazılı diyalog. Kullanıcı türü seçer; etkinlik seçildiği anda üretilir (kısa yükleme ekranı). Türü kullanıcı seçer, hangi öğelerin çalışılacağını tekrar motoru seçmeye devam eder: kullanıcı güçlü olduğu beceriyi seçse bile içerik zayıf ve vadesi gelen öğelerden gelir.
- **İlerleme:** bu hafta müfredatta nerede, kaç öğe öğrenildi ve kalıcılaştı, tekrar başarısı.
- Öneri ile kullanıcının gerçek seçimi ayrı kaydedilir; haftalık raporda hangi beceriye ne kadar zaman ayrıldığı görünür.

**Günlük döngü (10–15 dakika)**

1. Bugünün oturumu, kullanıcı gelmeden önce arka planda tek çağrıyla üretilir: tekrar motorunun seçtiği öğeler etrafında kullanıcının ilgi alanına ve seviyesine göre örnekler, metinler ve sorular. Yalnızca bu oturum önceden üretilir.
2. Kullanıcı Önerilen oturumla başlar. İsterse sonrasında "Ek çalışma"dan bir tür seçer; o etkinlik seçim anında üretilir.
3. Zayıf beceride daha çok etkinlik gelir (dinlemesi zayıf olana daha çok dinleme); hedefi günlük sohbet olana yazılı diyalog ağırlıklı etkinlikler gelir.
4. **Canlı geri bildirim:** yazma ve diyalogda en fazla 1–2 hata işaretlenir; önce ipucu, sonra Türkçe açıklama, öğrenci yeniden yazar. Hata çözümü direkt verilmez (soru YZ3).
5. Her etkinlikte "bu etkinlikte sorun var" düğmesi bulunur; bildirilenler denetime düşer.
6. Gün sonu özeti: bugün ne öğrendin, yarın ne tekrar edilecek.

**Haftalık (otomatik, her pazar)**

- Rapor: öğrenilen ve kalıcılaşan öğe sayısı, tekrar başarı oranı, en sık hata örüntüsü ve Türkçe açıklaması.
- Müfredat ajanı planı yeniden değerlendirir: hızlı ilerleyene fazlasını öne çeker, geride kalana tempoyu yavaşlatır. Değişiklik nedeniyle birlikte gösterilir.
- Pilotta ayrıca 1–2 soruluk memnuniyet ve "işe yaradı mı" geri bildirimi.

## 4. Mimari blueprint

Bu ürünün farkı, kararları LLM'e bırakmamak: neyin çalışılacağını, neyin ne zaman tekrar edileceğini ve ilerlemeyi kural katmanı belirler. LLM üç iş yapar: hedefe göre müfredat taslağı önerir, seçilen öğeler etrafında her kullanıcıya özel etkinliği üretir ve yazılanı değerlendirip hatayı etiketler. Hiçbir LLM çıktısı doğrulanmadan öğrenciye gitmez.

&#91;embedded content: MVP mimarisi · kural katmanı, LLM katmanı, iki veri deposu\]

Öğrenci modeli yalnızca olay kaydından hesaplanır; LLM modeli doğrudan yazmaz. Müfredat taslağı kural katmanında öğe havuzuna ve seviyeye karşı doğrulanır; üretilen her etkinlik ve geri bildirim şema, seviye ve yasaklı içerik denetiminden geçer ve olay kaydına yazılır. Panel, kullanıcıya müfredatı ve ilerlemeyi gösterir; "Önerilen" etiketini kural katmanının planından alır.

**Tasarım kuralları**

1. **Tekrar motoru LLM'den bağımsızdır.** Açık kaynak FSRS tipi bir bellek modeliyle başlanır (soru ÖB1); birim testle doğrulanır ve API maliyeti yoktur.
2. **Seçimi kural katmanı yapar, sarmalayı LLM üretir.** Hangi öğenin ne zaman çalışılacağı tekrar motorundan gelir; LLM o öğe için kullanıcının ilgisine ve seviyesine göre örnek, metin ve soru yazar. Böylece etkinlikler tamamen kişiye özel olur ama öğrenme planı ölçülebilir kalır.
3. **Müfredat ajanı öneri yapar, kural katmanı onaylar.** Taslak yalnızca havuzdaki öğelerden ve seviye sınırları içinde kurulabilir; hedef ve zayıf beceriye göre ağırlıklar (dinleme, yazılı diyalog vb.) taslakta görünür.
4. **Tek doğruluk kaynağı olay kaydıdır.** Öğrenci modelini bozarsak olay kaydından yeniden hesaplarız; üretilen etkinlik metinleri de kaydedilir, böylece sonradan denetlenebilir ve yeniden oynatılabilir.
5. **Seviye bir parametredir.** Her öğe CEFR seviyesi ve türüyle etiketlidir; B1–B2 genişlemesi yeni içerik ekler, mimariyi değiştirmez (soru VY11).
6. **Hata etiketi sabit bir şemadır.** LLM serbest metin değil, önceden tanımlı etiket kümesinden seçim yapar; Işıl'ın kontrol ettiği örnekler bu etiketlerin kalitesini ölçer.
7. **Maliyet kontrolü mimarinin parçasıdır.** Oturum tek çağrıyla önceden üretilir, bağlam minimumda tutulur, kullanıcı başına günlük çağrı limiti vardır, kolay etkinlikler ucuz modele yönlendirilebilir (model bir ayardır).

## 5. Veri modeli

Veri modelinin kuralı şu: **ham olay bir kez yazılır, türev durum olaylardan hesaplanır.** Böylece öğrenci modeli şemasını sonradan değiştirmek (örneğin tekrar algoritmasını ya da hata etiketlerini) eski veriyi çöpe atmaz.

| Varlık | Ana alanlar | Not |
| --- | --- | --- |
| Kullanıcı | id, hedef, günlük süre, ilgi alanları, onam zamanı, başlangıç tarihi | Ad ve e-posta dışında kişisel veri toplanmaz (veri minimizasyonu) |
| Öğe | id, tür (kelime, kalıp, yapı), İngilizce metin, Türkçe karşılık, CEFR seviyesi, kaynak liste, hata riski notu | İçerik deposunda küratörlü; seviye etiketi mimariyi seviyeden bağımsız tutar. Örnek cümleleri artık LLM üretir |
| Müfredat | kullanıcı, sürüm, hafta, haftalık odak, hedef öğe sayısı, hafta sonu "yapabileceği şeyler", beceri ağırlıkları, değişiklik nedeni | Müfredat ajanı önerir, kural katmanı doğrulayıp kaydeder; her yeniden planlama yeni sürüm olur |
| Olay | id, kullanıcı, zaman, tür (cevap, yazma, okuma, dinleme, geri bildirim tepkisi), öğe, sonuç, süre, ham veri | Yalnızca eklenir, hiç güncellenmez |
| Etkinlik kaydı | id, kullanıcı, öğeler, tür, üretilen içerik (tam metin), model ve prompt sürümü, önerilen mü, kullanıcı seçimi, doğrulayıcı sonucu, "sorun var" işareti | Üretilen her şey saklanır: denetim, yeniden oynatma ve önerinin etkisini ölçme için |
| Öğe durumu (türev) | kullanıcı, öğe, kararlılık, zorluk, son tekrar, sonraki tekrar, hatırlanabilirlik | Tekrar motoru yazar |
| Hata etiketi | kod, ad, Türkçe açıklama, ana dil kaynaklı mı, örnek | Sabit şema; LLM bu kümeden seçer |
| Hata kaydı | olay, etiket, cümle, düzeltme, öğrenci tepkisi | Hata örüntüsü buradan türetilir |
| Haftalık rapor | kullanıcı, hafta, özet metrikler, odak, oluşturulma zamanı | Türev; yeniden üretilebilir |

**Başlangıç hata etiketi kümesi (hipotez; Işıl ve hoca görüşmeleriyle düzeltilecek, sorular L1-1 ve L1-8):**

- Artikel eksik ya da fazla ("I have car").
- Özne eksik ("Is very nice"): Türkçe'de özne düşebilir.
- Be fiili eksik ya da yanlış ("She teacher").
- Kelime sırası: Türkçe'nin nesne-fiil sırasından aktarma.
- Edat seçimi (in, on, at).
- Çoğul eki, sayma adı ve saymayan ad karışıklığı.
- Zaman uyumsuzluğu ve üçüncü tekil kişi eki.

Bu küme tüm A1–A2 hatalarını kapsamaz; pilot sırasında en sık görülen "diğer" örneklerinden yeni etiket üretilir.

## 6. İçerik ve müfredat

Bu modelde **öğe listesi küratörlü, etkinlikler canlı üretilir.** Işıl ne öğretileceğini ve hangi hata riskinin izleneceğini belirler; LLM her kullanıcı için o öğeleri örnek, metin ve soruya dönüştürür. Üretim kalitesi öncesinde değil sonrasında denetlenir: doğrulayıcı her çıktıyı kontrol eder, Işıl haftalık örneklem inceler.

**Müfredat iskeleti.** A1–A2 hedefleri CEFR "yapabilir" tanımları, English Vocabulary Profile (kelime ve kalıp), English Grammar Profile (yapılar) ve Türkçe kaynaklı hata örüntülerinin kesişiminden seçilir (soru ÖT1). Bu profillerin ürün içinde yeniden kullanım koşulları henüz kontrol edilmedi; Faz 0'da lisans/kullanım şartları okunmalı.

**Başlangıç havuzu.** Yaklaşık 200 öğe (kelime, kalıp ve yapı karışık). Günlük yeni öğe sayısı ayrılan süreye bağlıdır: 10 dakikada 2, 15–20 dakikada 3, daha uzunda 4. Yani 8 hafta × 6 gün boyunca öğrenci 96–192 öğe görür; varsayılan 15 dakikada 144. Havuz en hızlı öğrenciye de yetecek büyüklükte tutulur. Her öğe için Türkçe karşılık ve en az bir hata riski notu hazırlanır; örnek cümleleri önceden yazmak gerekmez, yalnızca üretimi yönlendiren birkaç referans cümle yeterlidir.

**İçerik hattı**

1. Öğe listesi ve sırası küratörlü seçilir (Işıl'ın öğretmenlik bilgisi + profil listeleri).
2. Müfredat ajanı bu havuzdan kullanıcıya özel haftalık plan çıkarır; kural katmanı doğrular.
3. Her gün tekrar motoru çalışılacak öğeleri seçer; etkinlik üretici bunları kullanıcının ilgisine ve seviyesine göre oturuma dönüştürür.
4. Doğrulayıcı seviye, kelime, şema ve cevap sızıntısı kontrolünü yapar; geçemeyen etkinlik yeniden üretilir ya da yedek şablon kullanılır.
5. Işıl haftalık rastgele örnek ve "sorun var" işaretli etkinlikleri inceler; bulgular prompt ve kurallara geri döner.

| Etkinlik | Beceri | Amaç | Kim üretir |
| --- | --- | --- | --- |
| Hatırlama sorusu (boşluk doldurma, Türkçeden İngilizceye) | Kelime ve yapı | Aralıklı tekrar | Canlı üretilir; öğe seçimi tekrar motorundan |
| Yeni öğe sunumu (açıklama + örnek) | Kelime ve yapı | İlk karşılaşma | Canlı üretilir; örnekler kullanıcının ilgisine göre |
| Mikro okuma (50–80 kelime) ve anlama soruları | Okuma | Bağlamda kullanım | Canlı üretilir; seviye kuralı çok sıkı |
| Kısa yazma (1–2 cümle) | Yazma | Üretim ve geri bildirim | Öğrenci yazar; geri bildirimi canlı LLM üretir |
| Dinleme (cümle ve kısa metin) | Dinleme | Kulaktan anlama | Üretilen metin TTS ile seslendirilir; MVP'ye girer |
| Yazılı diyalog (rol yapma, 4–6 tur) | Yazma ve okuma | Günlük sohbet hazırlığı | Canlı LLM, seviye ve hedef öğeler sınırları içinde; konuşma (ses tanıma) Faz 2 |

**A1 için uyarı.** Çok düşük seviyede öğrenci İngilizce yazma yerine Türkçeden çeviri ya da sınırlı seçim sorularıyla başlamalıdır. İlk iki hafta yazma etkinliği cümle tamamlama olarak açılır (soru L1-8, hocalarla teyit edilecek).

## 7. LLM katmanı ve kalite

LLM artık yalnızca geri bildirim değil, tüm etkinlik içeriğini ürettiği için tek gerçek risk, yanlış ya da seviye dışı öğretmektir. Kalite **ayrı bir ölçüm hattıyla** denetlenir; model ya da prompt her değiştiğinde bu hat yeniden çalışır. Model adı bir ayardır: seçim değerlendirme setinin sonucuna göre yapılır ve değiştirilebilir.

**Yazma geri bildirimi çıktısı (yapılandırılmış, şema doğrulamalı)**

- Bulunan hatalar: cümledeki aralık, etiket kodu (sabit kümeden), açıklık düzeyi.
- En fazla 2 hata öne çıkarılır; kalanlar kaydedilir ama öğrenciye gösterilmez.
- Önce ipucu, sonra Türkçe açıklama; doğru cümle ancak öğrenci yeniden yazdıktan sonra gösterilir.
- Doğrulayıcı şema, etiket geçerliliği, seviye dışı kelime ve "cevabı doğrudan verme" kurallarını denetler; geçemeyen çıktı öğrenciye gitmez.

**Bağlam (context) tasarımı.** Prompt'a tüm geçmiş konmaz; yalnızca seviye, ilgili öğe ve son hatalı etiketler, hedef cümle ve öğrencinin yazdığı metin girer. Böylece maliyet düşük, davranış tekrarlanabilir kalır.

**Değerlendirme seti (altın set).** Işıl'ın etiketlediği yaklaşık 100 öğrenci cümlesi (doğru hata etiketi, kabul edilebilir düzeltmeler, doğruysa "hatasız"). Her değişiklikte şunlar ölçülür:

| Ölçüt | Ne gösterir | Hedef (doğrulanacak) |
| --- | --- | --- |
| Etiket doğruluğu | Hata türü doğru bulunuyor mu | Pilot öncesi eşik belirlenir |
| Aşırı düzeltme | Doğru cümleye hata deniyor mu | Mümkün olan en düşük |
| Cevabı ele verme | İpucu yerine doğrusunu söylüyor mu | Neredeyse sıfır |
| Yanlış öğretme | Açıklama dilbilgisi olarak yanlış mı | %2'nin altı |
| Seviye uyumu | A1–A2 dışı kelime/yapı kullanımı | Kural kontrolü çok sıkı |

**Canlı üretilen etkinliklerin denetimi.** Her etkinlik gösterilmeden önce otomatik kontrolden geçer: şema, seviye dışı kelime, hedef öğenin gerçekten kullanılması, cevabın sorunun içinde sızmaması, tek doğru cevap ve ses metni uyumu. Geçemeyen etkinlik bir kez yeniden üretilir, sonra yedek şablona düşer. Otomatik kontrol her hatayı yakalamaz; bu yüzden her etkinlikte "sorun var" düğmesi, Işıl'ın haftalık rastgele örneklemi (ilk pilot haftasında daha büyük) ve üretim sürümü kaydı bulunur. Kapsamlı "yanlış öğretme" oranı pilot sonunda bu örneklemden raporlanır.

**Hata durumu.** LLM zaman aşımına uğrarsa ya da çıktı doğrulamayı geçemezse öğrenciye "şimdilik atladık" denir ve cümle olay kaydına sonra işlenmek üzere yazılır. Günlük LLM çağrısı limiti maliyet kontrolü için kullanıcı başına konur. Bugünün oturumu kullanıcı gelmeden önce üretildiği için bekleme yalnızca ek çalışma seçiminde, yazılı diyalogda ve geri bildirimde hissedilir.

**Gizlilik.** LLM'e kullanıcı adı ya da e-posta gönderilmez; yalnızca rastgele kullanıcı kimliği ve metin. Kayıt sırasında 18 yaş üzeri onayı alınır. Saklama süresi ve silme talebi akışı pilot öncesi yazılır (soru ET alanı).

## 8. Teknoloji yığını önerisi

Hedef, tek kişinin 12 haftada kodlayabileceği, AB'de barınan ve sonra değiştirmesi kolay en yalın yapı. Aşağıdakiler **öneridir**: Emir'in alışkanlıkları ve hazır kredi durumu kesin seçimi belirler.

| Katman | Öneri | Neden | Alternatif |
| --- | --- | --- | --- |
| Arayüz | Next.js (React) + TypeScript, mobil öncelikli PWA | Tek kod tabanı, mağaza gerekmez | Vite + React |
| API | Python (FastAPI) | Tekrar, öğrenci modeli ve değerlendirme betikleri aynı dilde; ileride bilgi izleme (knowledge tracing) için kolay | TypeScript ile tek dil (ts-fsrs) |
| Veritabanı | PostgreSQL (olay tablosu JSONB) | Olay kaydı + türev tablolar tek yerde | Yönetilen Postgres (AB bölgesi) |
| Kimlik | E-posta bağlantısı ile giriş (parolasız) | Parola saklama yükü yok | Davet kodu |
| Tekrar motoru | Açık kaynak FSRS kütüphanesi | Hazır ve kanıtlı; birim testle doğrulanır | Kendi sade modelin |
| LLM | Bir sağlayıcı API'si, ince bir soyutlama arkasında; yapılandırılmış çıktı | Model değiştirmek tek ayar | İkinci sağlayıcı yedek |
| Seslendirme (esnek) | TTS API'si | Dinleme etkinliği için yeterli | Tarayıcı sesi (ücretsiz, düşük kalite) |
| Barındırma | AB bölgesinde yönetilen bir platform | GDPR ve kolay kurulum | Tek VPS |
| Ölçüm | Olay tablosu üzerinde SQL + bir not defteri (H1–H7) | Ek araç gerekmez | Hafif panel aracı |
| Kalite | Test + altın set betikleri, her değişiklikte | Regresyonu yakalar | — |

**Maliyet nasıl hesaplanır.** Yeni modelde pilot çağrısı yaklaşık 50 kullanıcı × günde 4 çağrı (oturum üretimi, yazılı diyalog ve geri bildirim) × 30 gün × 2 ay = yaklaşık 12.000 çağrıdır; önceki ön-üretimli taslağın yaklaşık iki katı. Yalnızca bugünün önerilen oturumu önceden üretilir (tüm türleri önceden üretmek boşa maliyet olurdu); oturum üretimi tek çağrıda yapılır ama çıktısı uzundur (metinler, sorular, dinleme sesleri), bu yüzden çağrı başı maliyet de daha yüksektir. Gerçek tutar sağlayıcının güncel fiyatıyla ve örnek bir oturumun token sayısıyla Hafta 1'de hesaplanıp başlangıç bütçesine yazılmalıdır. Maliyeti düşürme yöntemleri sonraya bırakılır ama tasarıma girer: aynı öğe için onaylı çıktıların önbelleğe alınıp yeniden kullanılması, kolay etkinlikler için daha ucuz model, bağlamın kısaltılması. Öğrenci ve girişim kredileri (Programlar sayfasındaki ilk satır) bu maliyeti karşılayabilir; Azure hatası çözülene kadar başka bir sağlayıcıyla başlamak engel değil, çünkü LLM katmanı soyutlanmıştır.

## 9. Haftalık roadmap

Yapı 12 hafta sürer (canlı üretim, müfredat ajanı ve panel 10 haftalık plana göre 2 hafta ekler), ardından 8 haftalık pilot gelir; her faz bir kapıyla biter. Hafta 1'in 9 Kasım 2026'da başladığını varsayarsak yapı 31 Ocak 2027'de, pilot 28 Mart 2027'de biter. Emir'in sınav dönemleri bilinmediği için tarihler kaydırılabilir; kapıların sırası kaymaz. Kapsam daraltmak gerekirse önce panelin süsleri ve yazılı diyalog kesilir, müfredat ve etkinlik üretimi kesilmez.

&#91;embedded content: MVP yol haritası · 4 faz, 4 kapı\]

Kapı 2 ve Kapı 3 kalite kapılarıdır: takvim kayarsa eşik düşürülmez, iş uzar. Şu hafta başlayacak ilk 3 iş: (1) LLM sağlayıcısını ve maliyet hesabını netleştirmek, (2) olay kaydı ve veri şemasının ilk sürümü, (3) Işıl'ın ilk 50 öğesini seçmesi.

## 10. Roller ve çalışma düzeni

Emir yapıyı kurar, Işıl öğretim kalitesinin sahibi olur; ikisi de kendi alanında son kararı verir ve kapı değerlendirmeleri ortak yapılır.

| Alan | Emir | Işıl |
| --- | --- | --- |
| Mimari ve kod | Sahibi | Ekran ve akış geri bildirimi |
| Tekrar motoru, öğrenci modeli, olay kaydı | Sahibi | — |
| LLM entegrasyonu ve değerlendirme hattı | Sahibi | Altın set etiketleme |
| İçerik: öğe listesi, sıra, haftalık etkinlik örneklem denetimi | Teknik format ve aktarım | Sahibi |
| Hata etiketi şeması ve Türkçe açıklamalar | Şema ve kod | İçerik ve doğruluk |
| Pilot kullanıcıları ve görüşmeler | Teknik destek, metrik | Hocalar ve çevre üzerinden bulma, görüşme |
| Notion soru listesi | Teknik sorular | Öğretim soruları |

**Çalışma düzeni (öneri).**

- Haftada bir 30 dakikalık ortak toplantı: geçen hafta ne bitti, kapıya ne kaldı, bu hafta kimin neye ihtiyacı var.
- Her hafta sonu Emir geçen haftanın ürününü Işıl'a 10 dakikada gösterir; Işıl öğretmen gözüyle yorumlar. Bu demo, içerik hatalarını en erken yakalayan kontroldür.
- Kararlar bu dokümanda ya da Notion'da tek satırla (tarih + karar + neden) kaydedilir; seviye kararında olduğu gibi.
- Notion soru listesi MVP'yi bloklamaz; Bölüm 11'deki sıralamaya göre kodu şekillendiren sorular önce, gerisi paralel kapatılır.

**Açık:** Işıl'ın haftalık ayırabileceği saat belli değil. İçerik küratörlüğü ve altın set etiketleme (yaklaşık 100 cümle) en çok onun zamanını alır; ilk haftada gerçek bir takvim çıkarılmalı.

## 11. Riskler, açık kararlar ve Notion soruları

Notion'daki soruların hepsi MVP'den önce kapanmak zorunda değil; aşağıdaki sıralama hangi sorunun hangi kapıdan önce cevaplanması gerektiğini gösterir. Cevapsız kalanlar "varsayım" olarak işaretlenir ve pilotta test edilir.

| Ne zamana kadar | Soru kodları | Neden |
| --- | --- | --- |
| Hafta 1–2 (kodu şekillendirir) | ÖB1 (tekrar modeli), ÖT1 (müfredat iskeleti), ÖT4 (kelime listesi), VY11 (seviye parametreli mimari) | Veri şeması ve öğe formatı buna bağlı |
| Hafta 4–6 (geri bildirim kalitesi) | GB1 ve GB2 (hangi hata, nasıl düzeltilir), L1-1 (Türkçe kaynaklı hatalar), L1-8 (Türkçe destek), YZ3 (cevabı vermenin zararı) | Kapı 2'nin eşiği ve hata etiketi şeması |
| Pilot öncesi | DÖ3 (CEFR eşleme), SK6 (beklenti ve süre), etik ve gizlilik soruları | Ölçüm ve onam ekranı |
| Pilot sırasında | ÜD1 ve ÜD10 (ödeme isteği, rakipler), MO1 (bağlılık), BC10 (ses tanıma) | Veri gerektirir; MVP bunu üretmek için var |

**Riskler ve önlemler**

| Risk | Önlem |
| --- | --- |
| Işıl'ın zamanı içerik darboğazı olur | İlk haftada gerçek takvim; havuz 200 öğeyle sınırlı; Işıl öğe listesini hazırlar, etkinlikleri yalnızca haftalık rastgele örneklemle ve "sorun var" bildirimleriyle inceler |
| Canlı üretim kalitesi dalgalı: yanlış ya da seviye dışı etkinlik, cevap sızıntısı | Otomatik doğrulayıcı, yedek şablon, "sorun var" düğmesi, üretim sürümü kaydı, ilk pilot haftasında geniş örneklem, Kapı 2 eşiği |
| Üretim maliyeti beklenenden yüksek (ön-üretimli taslaktan yaklaşık 2 kat çağrı) | Hafta 1'de gerçek token maliyeti; kullanıcı başına günlük çağrı limiti; onaylı çıktıları önbelleğe alma ve ucuz model sıralaması sonraki optimizasyon olarak tasarımda açık bırakılır |
| Gecikme ve kesinti: LLM yavaş ya da erişilemez | Bugünün oturumu kullanıcı gelmeden önce üretilir; ek çalışma seçiminde yükleme ekranı ve yedek şablon; yalnızca ek çalışma, diyalog ve geri bildirim canlı bekler |
| Ölçüm zorlaşır: her kullanıcı farklı içerik görüyor, öğrenme artışı neye bağlı? | Öğe ve beceri düzeyinde ortak ölçüm (aynı öğeler, aynı ön/son test); üretim sürümü kaydedilir; "Önerilen" etkisi gözlemsel okunur (kullanıcı seçimi karıştırıcıdır); tür seçimi serbest olduğu için rahat alana kayma riski haftalık raporda izlenir |
| Müfredat tahmini yanlış beklenti yaratır ("2 ayda B1" gibi) | Seviye vaadi yok, kilometre taşı ve aralık; haftalık yeniden plan nedenle gösterilir (soru SK6) |
| A1 düzeyinde öğrenci İngilizce yazamıyor | İlk iki hafta cümle tamamlama ve çeviri; yazma kademeli açılır |
| A1–A2'de ödeme isteği düşük, ücretsiz rakipler güçlü | Pilotta ödeme isteği testi; ürün farkını (kişisel müfredat ve hata analizi) gösteren karşılaştırma görüşmeleri |
| Kapsam kayar (konuşma, oyunlaştırma, yeni dil) | Bölüm 2'deki kapsam kuralı; zaman kıt olunca önce panel süsleri ve yazılı diyalog kesilir |
| Tek kişilik kodlama ve sınav dönemleri | Tarihler kayabilir, kapıların sırası ve eşikleri kaymaz |
| Veri gizliliği (KVKK ve GDPR) | Veri minimizasyonu, 18+ onayı, silme akışı, LLM'e kimlik gönderilmemesi |
| Pilot örneklemi küçük (30–50 kişi) | Sonuçlar yönsel okunur; kesin kanıt iddiası yapılmaz |
| Konuşma olmadan vizyon uzak kalır | Faz 2 planı açık yazılır; kullanıcıya MVP'nin kapsamı dürüstçe söylenir |
| Profil listelerinin (EVP ve EGP) kullanım koşulları bilinmiyor | Faz 0'da lisans okunur; gerekirse kendi öğe listemizi türetiriz |

**Açık kararlar:** Şirket yeri (İtalya ya da Türkiye), LLM sağlayıcısı ve gerçek üretim maliyeti (Hafta 1), 12 haftalık yapı takvimi (Emir'in sınav dönemlerine göre), Hafta 1'in başlangıç tarihi, Işıl'ın haftalık saati, proje adı (sonra dönülecek).
