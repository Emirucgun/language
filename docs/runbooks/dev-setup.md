# Geliştirme kurulumu

Hedef makine: Windows 10, 6 GB RAM. Docker kullanılmaz; PostgreSQL servis olarak kurulur.

## Araçlar

| Araç | Sürüm | Kurulum |
| --- | --- | --- |
| Git | 2.56 | `winget install Git.Git` |
| Node.js LTS | 26 | `winget install OpenJS.NodeJS.LTS` |
| uv | 0.13 | `winget install astral-sh.uv` |
| Python | 3.14 | `uv python install 3.14.10 --default` |
| PostgreSQL | 18 | `winget install PostgreSQL.PostgreSQL.18` |
| GitHub CLI | 2.102 | `winget install GitHub.cli`, sonra `gh auth login` |

Python 3.14 seçildi: 3.15 yeni çıktı, derlenmiş paketlerin tüm Windows tekerlekleri henüz garanti değil.

## Veritabanı

`postgres` süper kullanıcısı yalnızca yönetim için; şifresi `.secrets/postgres-local.env` dosyasında, depoya girmez. Servis `postgresql-x64-18`, port 5432.

```sql
CREATE ROLE teacher_owner LOGIN PASSWORD '...';
CREATE ROLE teacher_app LOGIN PASSWORD '...';
CREATE DATABASE teacher_dev OWNER teacher_owner;
CREATE DATABASE teacher_test OWNER teacher_owner;
```

`teacher_owner` göçleri çalıştırır; `teacher_app` çalışma zamanıdır, `events` üzerinde `UPDATE` ve `DELETE` yetkisi yoktur.

## API

`api/.env.example` dosyasını `api/.env` olarak kopyalayıp doldurun. `.env` depoya girmez.

```bash
cd api
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_dev_content
uv run python -m scripts.import_cefrj
uv run fastapi dev app/main.py
```

`import_cefrj` için önce kaynak dosya indirilir: kök `README.md`. Arka plan işleri ayrı süreçtir: `uv run python -m app.worker`.

## Web

```bash
cd web
npm ci
npm run dev
```

## Worktree'de çalışmak

Worktree'de `api/.env`, `.venv` ve `node_modules` yoktur. `TEST_DATABASE_URL` yoksa veritabanı testleri atlanır. Ana checkout ile worktree aynı `teacher_dev` veritabanını kullanır: dalda yeni göç varsa ana checkout o göçü tanımaz, bu yüzden dal birleşmeden `teacher_dev`e uygulamayın.
