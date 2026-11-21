# A1–A2 AI İngilizce Özel Öğretmen (MVP)

Ürün belgesi ve iş listesi `MD files/` altında:

- `MVP Roadmap ve Blueprint – A1–A2 AI İngilizce Özel Öğretmen.md`: ne ve neden
- `Düzeltme ve Geliştirme Listesi.md`: sıradaki işler

Teknik belgeler, durum tablosu ve kararlar: [docs/](docs/README.md). Yapay zeka aracı kuralları: [AGENTS.md](AGENTS.md).

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

Veritabanı ve içerik (api/ içinde):

```bash
uv run alembic upgrade head
uv run python -m scripts.seed_dev_content
uv run python -m scripts.import_cefrj
uv run python -m app.worker
```

`import_cefrj` için önce [CEFRJ_wordlist_ver1.6.zip](https://www.cefr-j.org/data/CEFRJ_wordlist_ver1.6.zip) indirilip içindeki Excel `content/sources/cefrj-1.6/cefrj-wordlist-1.6.xlsx` olarak konur (depoda tutulmaz).

## Atıflar

- Kelime seviyeleri: *CEFR-J Wordlist Version 1.6*, Tono Laboratuvarı (Yukio Tono), Tokyo Yabancı Diller Üniversitesi. <https://www.cefr-j.org/download.html> — atıfla araştırma ve ticari kullanım serbesttir.
- Çekim biçimleri: [lemminflect](https://github.com/bjascob/LemmInflect) (MIT), yalnızca içe aktarma sırasında.
