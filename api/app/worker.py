"""Worker giriş noktası: `uv run python -m app.worker`.

psycopg'nin asenkron modu Windows'un varsayılan Proactor döngüsüyle çalışmaz; bu yüzden
döngü açıkça Selector olarak seçilir (Linux'ta fark etmez).
"""

import asyncio
import logging

from app.jobs import app


async def main() -> None:
    async with app.open_async():
        await app.run_worker_async()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
