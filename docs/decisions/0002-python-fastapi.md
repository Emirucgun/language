# ADR-0002: API için Python ve FastAPI

Tarih: 2026-11-03 · Durum: kabul edildi

## Bağlam
Tek kişilik proje. Ürünün çekirdeği tekrar motoru, öğrenci modeli, doğrulayıcı, altın set betikleri ve pilot analizi. Makine 6 GB RAM.

## Karar
API Python ve FastAPI ile, arayüz Next.js ile yazılır; iki dilin yükü tipleri OpenAPI şemasından üreterek azaltılır.

## Alternatifler
- Tamamen TypeScript: `ts-fsrs` var, ama değerlendirme ve analiz tarafı yine Python'da kalırdı.
- Docker: WSL2 ve Docker Desktop bu makinede geliştirmeyi yavaşlatır.
- Redis ve Celery: procrastinate Postgres üzerinde yeterli; bir altyapı parçası eksilir.
- Hazır kimlik servisi: pilot 50 kişi; kendi magic link akışımız yaklaşık bir günlük iş ve veriyi tek yerde tutar.

## Sonuçlar
Çekirdek tek dilde kalır ve ileride knowledge tracing'e açıktır. İki dil ek yüktür: iş mantığı Next route handler'larında yazılmaz, tipler elle tutulmaz (`npm run gen:api`).
