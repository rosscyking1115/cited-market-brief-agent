"""CI guard: every org-scoped table must be covered by an RLS policy.

Adding a new table with org_id and forgetting isolation fails this test —
the cross-tenant gate cannot silently regress.
"""

from app.db.base import Base
from app.db.rls import generate_rls_ddl, org_scoped_tables


def test_every_org_id_table_has_a_policy() -> None:
    ddl = generate_rls_ddl()
    for table, column in org_scoped_tables().items():
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in ddl
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in ddl
        assert f"CREATE POLICY tenant_isolation ON {table}" in ddl
        assert f"({column} = current_setting" in ddl.split(f"ON {table} USING ")[1].split(";")[0]


def test_known_tenant_tables_are_scoped() -> None:
    scoped = org_scoped_tables()
    for table in (
        "organizations", "users", "watchlists", "sources", "documents", "chunks",
        "time_series", "briefs", "claims", "citations", "exports", "feedback",
        "audit_events",
    ):
        assert table in scoped, f"{table} must be tenant-scoped"


def test_global_tables_are_not_scoped() -> None:
    scoped = org_scoped_tables()
    assert "eval_runs" not in scoped  # evals are global, by design
    assert "entities" not in scoped  # public reference data (tickers/CIKs)


def test_fail_closed_policy_shape() -> None:
    # current_setting(..., true) -> NULL when unset -> policy false -> zero rows
    assert "current_setting('app.current_org_id', true)::uuid" in generate_rls_ddl()


def test_no_unpoliced_org_tables_sneak_in() -> None:
    """If a model adds org_id, it must appear in the DDL (count parity)."""
    ddl = generate_rls_ddl()
    org_tables = [t.name for t in Base.metadata.tables.values() if "org_id" in t.columns]
    for name in org_tables:
        assert f"ON {name} USING" in ddl
