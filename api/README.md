# api

FastAPI uygulaması ve procrastinate arka plan işleri. Mimari ve kararlar: `../MD files/Technical MVP – A1–A2 AI İngilizce Özel Öğretmen.md`.

```bash
uv sync
uv run fastapi dev app/main.py
uv run pytest
uv run ruff check . && uv run mypy
```

Ayarlar `.env.example` dosyasından `.env` olarak kopyalanır.
