"""Kullanıcının rolünü değiştirir. Kullanıcı önce davetle giriş yapmış olmalıdır.

cd api
uv run python -m scripts.set_role isil@ornek.com reviewer
"""

import argparse
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv()

from app import models  # noqa: E402, F401 - tüm tabloları kaydeder
from app.auth.models import ROLES, User  # noqa: E402
from app.config import settings  # noqa: E402
from scripts.sheets import utf8_output  # noqa: E402


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Kullanıcı rolünü değiştirir.")
    parser.add_argument("email")
    parser.add_argument("role", choices=ROLES)
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        user = session.query(User).filter(User.email == args.email).one_or_none()
        if user is None:
            sys.exit("Kullanıcı yok: önce davetle giriş yapmalı.")
        user.role = args.role
        session.commit()
    engine.dispose()
    print(f"Rol güncellendi: {args.role}")


if __name__ == "__main__":
    main()
