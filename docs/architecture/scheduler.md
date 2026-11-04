# Tekrar motoru

`app/scheduler/`: py-fsrs 6, hedef hatırlama 0,9, bulanıklaştırma kapalı (yeniden oynatma deterministik olsun diye).

## Derece eşlemesi

| Cevap | Derece |
| --- | --- |
| Yanlış | Again |
| İpuçlu doğru | Hard |
| Doğru | Good |

Easy kullanılmıyor. Yazma için yalnızca doğrulayıcıdan geçen geri bildirim derece üretir (`writing_assessed`). Okuma soruları ve diyalog cümleleri derecelendirilmez. Şıklı doğruyu Good saymak kararlılığı şişirir: DZ-5.

## Durum

Her öğe durumu işlediği son olayı (`last_event_id`, filigran) tutar. `update_item_states` artımlı ilerler, `rebuild_item_states` sıfırdan hesaplar, `find_mismatches` ikisini karşılaştırır. Olay yazan kod ve durum güncellemesi aynı kullanıcı kilidini (`lock_user`) alır.

## Öğe seçimi

`select_items`: önce vadesi gelenler (en gecikmiş önce), sonra müfredat sırasındaki yeni öğeler. Tekrar birikmişse yeni öğe kotası yarıya iner.

**Vade kesimi.** Günlük oturum yerel gün sonunu kullanır: gece üretilen oturum gün içinde vadesi dolacakları da kapsar. Serbest yazma şu an + 1 saat, ek çalışma şu an + 1 gün kullanır.

## Günlük kota

Tek tanım `app/scheduler/quotas.py`; oturum üretimi ve müfredat kapasitesi buradan okur.

| Günlük süre | En fazla tekrar | En fazla yeni öğe | 8 haftada |
| --- | --- | --- | --- |
| 10 dakikaya kadar | 4 | 2 | 96 |
| 20 dakikaya kadar (varsayılan 15) | 6 | 3 | 144 |
| Daha uzun | 8 | 4 | 192 |

Çalışma günü haftada 6'dır. Kapasite = günlük yeni öğe × 6. Tempo kuralı: [flows.md](flows.md#haftalık-rapor-ve-yeniden-plan).
