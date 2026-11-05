"""Pilot davet kodları üretir ve ekrana yazar.

cd api
uv run python -m scripts.create_invites 5 --note "alfa grubu"
"""

import argparse
import secrets

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv()

from app import models  # noqa: E402, F401 - tüm tabloları kaydeder
from app.auth.models import Invite  # noqa: E402
from app.config import settings  # noqa: E402
from scripts.sheets import utf8_output  # noqa: E402

# Karışmaya müsait karakterler (0/O, 1/I/l) yok: kod elle de yazılabilsin.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int)
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        codes = [new_code() for _ in range(args.count)]
        session.add_all(Invite(code=code, note=args.note) for code in codes)
        session.commit()
    engine.dispose()
    print("\n".join(codes))


if __name__ == "__main__":
    main()
