# Tablolar

Işıl içeriği Google Sheets'te yazar, Emir içe aktarır. Ayrı bir ekran yoktur.

| Şablon | Ne için | Nereye gider |
| --- | --- | --- |
| `oge-tablosu.xlsx` | Öğe havuzu | `content.items` |
| `altin-set.xlsx` | Geri bildirim ölçümü | `eval/golden/feedback.jsonl` (depoda) |
| `hata-etiketleri.xlsx` | Etiket adları ve açıklamaları; taslak etiketlerle dolu | `content.error_tags` |
| `yerlestirme-inceleme.xlsx` | 24 soru için Onay / Değiştir / Çıkar; taslak sorularla dolu | `content.fixed_tests` |

Şablonlar `content/templates/` altındadır. Sütunlar değişirse `api/` içinde yeniden üretilir: `uv run python -m scripts.make_templates`. Sütun açıklamaları her dosyanın `Açıklama` sayfasındadır.

## Akış

1. Emir şablonu Drive'a yükler, Sheets olarak açar ve Işıl'la paylaşır.
2. Işıl `Veri` sayfasını doldurur. Başlıkları ve sayfa adını değiştirmez.
3. Emir dosyayı `.xlsx` olarak indirir ve raporu alır:

   ```bash
   uv run python -m scripts.import_items dosya.xlsx
   ```

4. Rapordaki satırları Işıl düzeltir (`satır 12: Seviye boş`). Bu adım hata kalmayana kadar tekrarlanır.
5. Emir yazar: aynı komuta `--apply` eklenir. Yerleştirme için `--apply --reviewer "Işıl"`.

Sıra önemlidir: altın set etiketleri katalogla karşılaştırır, bu yüzden önce hata etiketleri aktarılır.

## Kurallar

- `--apply` yoksa hiçbir şey yazılmaz. Tek bir hata varsa da hiçbir satır yazılmaz; uyarılar engellemez.
- Öğe satırı silinirse öğe pasifleşir, öğrenci geçmişi korunur. Türkçe karşılığı düzeltilen öğe kimliğini korur.
- Gerçek havuz yazılınca `dev-seed` öğeleri pasifleşir.
- Aynı İngilizce öğe farklı Türkçe karşılıkla iki satır olabilir (light: ışık, hafif).
- Etiket listesi değişirse feedback prompt'u değişir; altın set yeniden koşulur.
- Yerleştirmede hepsi Onay ise mevcut sürüm onaylanır; değişiklik varsa yeni sürüm açılır, eski sürüm kalır.
- Altın sette bölme boşsa cümleden kararlı olarak üretilir (yaklaşık %30 `dev`). `test`teki bir cümle `dev`e alınamaz.
