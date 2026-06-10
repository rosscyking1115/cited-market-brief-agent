"""Create the pgvector extension and all tables for local development.

Usage (from backend/, with docker compose db running):
    python scripts/bootstrap_db.py

For tracked migrations use Alembic instead:
    alembic revision --autogenerate -m "initial schema" && alembic upgrade head
"""

from sqlalchemy import text

from app.db.base import Base, get_engine
from app.db import models  # noqa: F401 — register all tables


def main() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)
    print(f"Created {len(Base.metadata.tables)} tables:")
    for name in sorted(Base.metadata.tables):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
