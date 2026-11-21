# ADR-0001: OpenAI hesabı ve işleme bölgesi

Tarih: 2026-11-04 · Durum: önerildi

## Bağlam

OpenAI'ye geçiş için tek proje ve tek anahtar gerekiyor (OA-1). OpenAI'nin sayfaları AB işleme konusunda farklı anlatıyor: blog "yeni projede Europe seç" diyor, veri sayfası satış ve onay gerektiriyor; AB işleme uygun modellerde %10 ek ücretli. 3 Kas 2026'da Emir pilot için AB dışı LLM işlemenin kabul edilebilir olduğunu söyledi; uygulama ve veritabanı AB'de kalıyor, modele ad ve e-posta gitmiyor.

## Karar

Pilotta standart işleme bölgesiyle tek OpenAI projesi kullanılır; AB işleme ve sıfır veri saklama için satışa soru açılır, yanıt gelene kadar pilot bunu beklemez.

## Alternatifler

- AB bölgesi şimdi: satış onayı gerekiyor olabilir ve pilotun takvimini ona bağlar; ayrıca Realtime ve `gpt-transcribe` için uygunluğu doğrulanmadı.
- Sıfır veri saklamayı beklemek: kötüye kullanım günlükleri 30 güne kadar tutuluyor, ama modele kimlik bilgisi gitmediği için pilotu durdurmaya değmez.

## Sonuçlar

- Kolaylaşan: anahtar hemen kullanılabilir, TTS ve karşılaştırma ilerler.
- Zorlaşan: onam metni yurt dışı aktarımı açıkça söylemeli (DZ-11); hukuki görüş bu kararı değiştirebilir.
- İzlenecek: satış yanıtı, hukuki görüş.

Kabul edilmesi için kalan: OpenAI projesinde harcama limitinin ayarlandığının teyidi ve satışa sorunun gönderilmesi (Emir).
