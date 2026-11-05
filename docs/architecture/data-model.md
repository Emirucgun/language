# Veri modeli

Üç kural: olay bir kez yazılır ve türev tablolar olaylardan yeniden üretilebilir; her bilgi tek yerde durur; LLM'in o an ne gördüğü yeniden kurulabilir (prompt sürümü + öğrenci özeti + görev girdisi). Alan adları kodda İngilizcedir. Tam alan listesi kaynağı modellerdir (`api/app/*/models.py`); bu belge neden'i anlatır.

## `content` şeması

Küratörlü ve sürümlü; uygulama rolü yalnızca okur. İçe aktarma: [tablolar](../content/tablolar.md).

| Tablo | Not |
| --- | --- |
| `items` | Öğe havuzu. `kind`: word, chunk, structure. `forms`: doğrulayıcı için çekimli biçimler. `reference_sentences`: `[{en, tr}]`; içe aktarıcı doldurur, henüz okuyan yok (DZ-3) |
| `vocab_allowlist` | Doğrulayıcının seviye sözlüğü (CEFR-J) |
| `error_tags` | Türkçe açıklamanın tek kaynağı; LLM yalnızca kod seçer |
| `fixed_tests` | Sabit, sürümlü ölçüm testleri. `purpose`: placement, pre, post, retention. Yalnızca placement kullanılıyor |

## `learning` şeması

| Tablo | Not |
| --- | --- |
| `users` | Kişisel veri yalnızca `email` ve `display_name`. `role`: learner, reviewer |
| `invites`, `login_tokens`, `auth_sessions` | Düz token saklanmaz |
| `curricula` | Her yeniden plan yeni satır (`version`) |
| `study_sessions` | Günde bir "bugünün oturumu" |
| `activity_contents` | Üretilen içeriğin tek kopyası; uygunsa kullanıcılar arasında paylaşılır (`shareable`). `status`: approved, rejected, retired |
| `activities` | Bir içeriğin bir kullanıcıya gösterimi; aynı kişiye aynı içerik bir kez (unique). `origin`: session, extra, template |
| `events` | **Tek doğruluk kaynağı**, yalnızca eklenir. Öğrencinin yazdığı metin yalnızca burada |
| `feedbacks` | Açıklama metni saklanmaz, katalogdan okunur. `status`: shown, rejected, deferred |
| `error_marks` | Hata örüntüleri buradan türetilir; en fazla 2'si `shown` |
| `item_states` | Türev FSRS durumu; `last_event_id` filigrandır |
| `learner_snapshots` | LLM'e giden öğrenci özeti; günde bir donar |
| `weekly_reports` | Türev; kullanıcının gördüğü hal saklanır |
| `llm_calls` | `provider`: anthropic, openai. Prompt metni saklanmaz. Ham yanıt yalnızca hatada (`raw_on_failure`); 30 gün temizliği henüz yok (EK-14) |
| `reviews` | Işıl'ın kararları. `verdict`: correct, wrong_teaching, off_level, unclear. `source`: sample, flag; H4 yalnızca `sample`dan hesaplanır |

## Olaylar

Şemalar `api/app/events/schemas.py`; her olay `schema_version` taşır ve payload Pydantic ile doğrulanır.

`consent_given`, `goal_set`, `fixed_test_answer`, `fixed_test_completed`, `curriculum_created`, `curriculum_replanned`, `activity_shown`, `answer_submitted`, `writing_submitted`, `rewrite_submitted`, `writing_assessed`, `feedback_shown`, `feedback_reaction`, `activity_flagged`, `extra_activity_chosen`, `dialogue_replied`, `session_completed`, `report_viewed`, `nps_submitted`.

Derecelendirilmiş olaylar istemciden yazılamaz: istemci yalnızca `events/router.py`'deki izin listesini gönderebilir.

## Hipotezlerin verisi

| Hipotez | Kaynak |
| --- | --- |
| H1 hatırlama | `fixed_tests` ve olaylar (henüz yok: DZ-3) |
| H2 aktiflik | olaylar |
| H3 ön ve son test | `fixed_tests` ve olaylar (henüz yok: DZ-4) |
| H4 doğruluk | `reviews`, yalnızca `source = sample` |
| H5 anlaşılırlık | `feedback_reaction` |
| H6 memnuniyet | `nps_submitted` |
| H7 öneri | `activities.recommended`, `extra_activity_chosen` |

## Sabit testler

Etkinlikler canlı üretilir; ama yerleştirme, ön ve son test ile 14 gün hatırlama testi canlı üretilmez. Kullanıcılar arasında karşılaştırılabilir ölçüm için sabit, sürümlü ve Işıl onaylı olmalıdır. Hatırlama testi için bu kural DZ-3'te yeniden tasarlanacak: öğrenciler öğeleri farklı günlerde öğrendiği için sabit bir test 14 gün sonrasını ölçemez.
