# Kimlik ve gizlilik

## Giriş

Akış: e-posta → yeni kullanıcıysa davet kodu → tek kullanımlık bağlantı → `httpOnly`, `SameSite=Lax` oturum çerezi (yerel dışında `Secure`). Oturumlar sunucu tarafındadır, iptal edilebilir.

- `POST /api/auth/request`: bilinmeyen e-postada ve davetsiz istekte sessizce hiçbir şey yapmaz; yalnızca geçersiz davet kodu 400 döner. E-posta başına saatte 5 bağlantı.
- `POST /api/auth/verify`: bağlantı tek kullanımlık, 15 dakika. Yeni kullanıcıda davet ancak bu anda harcanır.
- Oturum 30 gün. Token'ların yalnızca SHA-256 özeti saklanır.
- E-posta Brevo SMTP ile gider (`app/auth/email.py`). `SMTP_HOST` boşsa yerelde bağlantı loga yazılır. Gönderim hatasında istek 503 ile geri alınır.

Davet kodu: `uv run python -m scripts.create_invites 5`. Rol: `uv run python -m scripts.set_role e-posta reviewer`; rol başka yoldan verilmez.

## Yetki

| Bağımlılık | Şart |
| --- | --- |
| `CurrentUser` | Geçerli oturum |
| `ConsentedUser` | Onam ve 18+ onayı; öğrenme uç noktaları için, yoksa 403 |
| `ReviewerUser` | `role = reviewer`; inceleyenden onam istenmez |

İnceleyen öğrencinin metnini görür, kimliğini görmez.

## LLM'e giden veri

Ad ve e-posta prompt'a girmez. **Gidenler:** öğrencinin yazdığı metin, hedef, günlük süre, seviye, zayıf beceri, ilgi alanları, en sık hata kodları.

- Öğrenci metninde e-posta varsa istek 422 ile reddedilir, hiçbir şey saklanmaz, metin ekranda kalır (`deps.reject_personal_data`). İlgi alanı için de aynısı.
- `generate_structured` içindeki koruma son savunma hattıdır: e-posta deseni bulursa çağrıyı yapmaz, `None` döner ve adresi kaydetmez.
- Koruma yalnızca e-postayı tanır. Telefon, ad gibi bilgiler için "kişisel bilgi yazmayın" uyarısı planlanıyor (DZ-11).
- İlgi alanları serbest metin olduğu için hem enjeksiyon hem uygunsuz içerik kapısıdır; listeden seçime dönecek (DZ-10).

## Silme

**Henüz uygulanmadı (DZ-11).** Onam metni silme hakkı vaat ediyor, ama silme ucu ve `redact_user` yok. Plan: `users` üzerindeki kişisel alanlar boşaltılır, `deleted_at` dolar; `events` içindeki öğrenci metinleri sahip rolüyle çalışan ve kendisi de kayıt bırakan tek bir işlemle silinir. Yalnızca-ekleme kuralının tek istisnası budur. Olaylar analiz bütünlüğü için kalır. Saklama süresi pilot öncesi yazılır.

## Barındırma ve aktarım

Uygulama ve veritabanı AB'de kalır. LLM işleme pilotta AB dışında olabilir: [ADR-0001](../decisions/0001-openai-hesap-ve-bolge.md), [ADR-0006](../decisions/0006-llm-saglayici-claude.md). Hukuki dayanak ve onam metni pilot öncesi netleşecek (DZ-11).
