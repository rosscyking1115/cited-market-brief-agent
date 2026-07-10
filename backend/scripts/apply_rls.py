"""Generate (and optionally apply) the tenant-isolation RLS policies.

python scripts/apply_rls.py            # print DDL
python scripts/apply_rls.py --apply    # apply to DATABASE_URL
"""

import sys

from app.db.rls import generate_rls_ddl


def main() -> None:
    ddl = generate_rls_ddl()
    print(ddl)
    if "--apply" in sys.argv:
        from sqlalchemy import text

        from app.db.base import get_engine

        with get_engine().begin() as conn:
            for statement in ddl.splitlines():
                stmt = statement.strip()
                if stmt and not stmt.startswith("--"):
                    conn.execute(text(stmt))
        print("-- applied --")


if __name__ == "__main__":
    main()
