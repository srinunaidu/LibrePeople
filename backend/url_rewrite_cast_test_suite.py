"""Focused regression: portable CAST in app/storage/url_rewrite LIKE predicates.

Background: ``rewrite_prefix`` / ``count_legacy_files_urls`` issued bare
``column.like(...)``. On PostgreSQL a reflected native-enum column (e.g.
``leave_ledger.entry_type``) is a ``String`` subclass, so PG renders
``<enumtype> ~~ unknown`` and raises ``UndefinedFunction`` (breaks PG callers
such as ``scripts/verify_files_urls.py``). The fix wraps both LIKE receivers
in portable ``cast(column, Text)`` — never the PG-only ``::`` operator — so
SQLite behavior is identical (CAST is a no-op there).

Checks (run everywhere, no PG needed):

* No bare ``.like()`` / ``.ilike()`` without a ``cast()`` receiver remains in
  ``app/storage/url_rewrite.py`` (AST scan, same style as the gate-A scan in
  ``pg_enum_checkfirst_test_suite.py``).
* SQLite rewrite results are unchanged: count reports 2 legacy rows, rewrite
  returns the same column, exact post-rewrite values, legacy empty after,
  second run is a no-op (idempotent).

Run:  python url_rewrite_cast_test_suite.py
"""
import ast
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "SECRET_KEY", "local-test-secret-key-not-for-production-0123456789"
)
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["BACKEND_CORS_ORIGINS"] = ""

from sqlalchemy import create_engine, text  # noqa: E402

from app.storage.url_rewrite import (  # noqa: E402
    NEW_PREFIX,
    OLD_PREFIX,
    count_legacy_files_urls,
    rewrite_prefix,
)

_PASS, _FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _FAIL.append((name, exc))
        print(f"FAIL  {name}: {exc!r}")
    else:
        _PASS.append(name)
        print(f"PASS  {name}")


def test_no_bare_like_without_cast():
    """Every .like/.ilike receiver in url_rewrite.py is a cast(...) call."""
    source = (BACKEND_DIR / "app" / "storage" / "url_rewrite.py").read_text()
    tree = ast.parse(source)
    bare = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("like", "ilike")
            and not (
                isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Name)
                and node.func.value.func.id == "cast"
            )
        ):
            bare.append(f"line {node.lineno}: .{node.func.attr}() without cast() receiver")
    assert not bare, "; ".join(bare)


def _seeded_engine(path):
    e = create_engine(f"sqlite:///{path}")
    with e.begin() as conn:
        conn.execute(
            text("CREATE TABLE documents (id INTEGER PRIMARY KEY, doc_url VARCHAR(255), notes TEXT)")
        )
        conn.execute(
            text(
                "INSERT INTO documents (doc_url, notes) VALUES "
                "('/files/a.pdf', 'x'), ('/files/b/c.pdf', NULL), "
                "('plain.txt', 'keep'), ('/other/d.pdf', 'keep')"
            )
        )
    return e


def test_sqlite_rewrite_results_identical():
    """CAST is a no-op on sqlite: same rewrite results as before the fix."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        e = _seeded_engine(tmp)
        before = count_legacy_files_urls(e)
        assert len(before) == 1 and before[0]["rows"] == 2, before
        changed = rewrite_prefix(e, OLD_PREFIX, NEW_PREFIX)
        assert "documents.doc_url" in changed, changed
        with e.connect() as conn:
            rows = conn.execute(text("SELECT doc_url, notes FROM documents ORDER BY id")).all()
        assert [r[0] for r in rows] == [
            "/api/v1/files/a.pdf",
            "/api/v1/files/b/c.pdf",
            "plain.txt",
            "/other/d.pdf",
        ], rows
        assert [r[1] for r in rows][2] == "keep"
        assert count_legacy_files_urls(e) == []
        # Idempotent: a second run changes nothing.
        assert rewrite_prefix(e, OLD_PREFIX, NEW_PREFIX) == []
        e.dispose()
    finally:
        os.unlink(tmp)


def main():
    for name, fn in [
        ("no bare LIKE without CAST in url_rewrite.py", test_no_bare_like_without_cast),
        ("sqlite rewrite results identical after CAST fix", test_sqlite_rewrite_results_identical),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
