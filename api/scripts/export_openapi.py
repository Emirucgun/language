"""FastAPI şemasını dosyaya yazar; arayüz tipleri buradan üretilir (`npm run gen:api`).

uv run python -m scripts.export_openapi ../web/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1])
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{target} yazıldı")


if __name__ == "__main__":
    main()
