# A1–A2 AI İngilizce Özel Öğretmen (MVP)

Ürün ve teknik kararlar `MD files/` altında:

- `MVP Roadmap ve Blueprint – A1–A2 AI İngilizce Özel Öğretmen.md`: ne ve neden
- `Technical MVP – A1–A2 AI İngilizce Özel Öğretmen.md`: nasıl

## Yapı

| Klasör | İçerik |
| --- | --- |
| `web/` | Next.js arayüzü (PWA); `/api/*` isteklerini FastAPI'ye yönlendirir |
| `api/` | FastAPI uygulaması, Alembic göçleri, arka plan işleri |
| `content/` | Öğe havuzu, hata etiketleri, sabit testler |
| `eval/` | Altın set ve analiz not defterleri |

## Yerelde çalıştırma

Gereksinimler: Node.js 26 LTS, uv, Python 3.14, PostgreSQL 18.

```bash
cd api
uv sync
uv run fastapi dev app/main.py
```

```bash
cd web
npm install
npm run dev
```

`api/.env.example` dosyasını `api/.env` olarak kopyalayıp doldurun.
