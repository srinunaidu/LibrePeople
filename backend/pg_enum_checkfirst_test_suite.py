"""PostgreSQL native-enum regression suite (gate A: 0012 enum collision).

Background: the 0001 baseline runs ``metadata.create_all`` over the frozen
tables, which on PostgreSQL creates the native enum type
``leaveledgerentrytype`` even though the owning ``leave_ledger`` table is not
in the frozen set. Revision 0012 then created the same table with a plain
``sa.Enum(name=...)``, and Alembic's ``op.create_table`` emits an
unconditional ``CREATE TYPE`` (``checkfirst=False`` is hard-coded in
``alembic/ddl/impl.py``), so the chain died on PostgreSQL with
``type "leaveledgerentrytype" already exists`` while SQLite/Oracle stayed
green (enums compile to VARCHAR there). The fix: every named enum used by a
migration declares ``create_type=False`` and is created idempotently with
``.create(bind, checkfirst=True)``.

Two tests:
1. **Static scan** — parses every file in ``migrations/versions`` and fails
   if any ``sa.Enum``/``postgresql.ENUM`` with a ``name=`` (i.e. a real PG
   native type) lacks ``create_type=False``. Runs everywhere, no PG needed.
2. **PG-gated chain** — upgrades a scratch PostgreSQL database to head.
   Runs only when ``ALEMBIC_DATABASE_URL`` (or ``PG_PROOF_URL``) points at a
   reachable PostgreSQL; otherwise SKIPS with a reason and never fails.
3. **Static scan (gate A: lp_files_url_rewrite enum-LIKE)** — parses every
   file in ``migrations/versions`` and fails on any bare ``.like(...)`` /
   ``.ilike(...)`` whose receiver is not a ``cast(...)`` call. On PG a
   reflected native-enum column is a ``String`` subclass, so a bare
   ``<enum-col> LIKE`` renders ``<enumtype> ~~ unknown`` and PG raises
   ``UndefinedFunction``; ``CAST(<col> AS TEXT)`` is portable and identical
   on SQLite. Runs everywhere, no PG needed.

Run:  python pg_enum_checkfirst_test_suite.py
"""
import ast
import os
import subprocess
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
os.environ.setdefault("DATABASE_URL", "sqlite:///./pg_enum_suite_scratch.db")

RESULTS = {"pass": 0, "fail": 0, "skip": 0}
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def skip(name: str, reason: str) -> None:
    RESULTS["skip"] += 1
    print(f"  SKIP  {name}  ({reason})")


def _enum_calls_without_checkfirst(path: Path) -> list[str]:
    """Named-enum constructor calls in one file missing create_type=False."""
    tree = ast.parse(path.read_text(), filename=str(path))
    # Enum constructors used only as the receiver of an idempotent
    # `.create(bind, checkfirst=True)` are the approved pattern, not an
    # unconditional CREATE TYPE. Exempt exactly those call nodes.
    idempotent: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "create"
            and isinstance(func.value, ast.Call)
            and any(
                kw.arg == "checkfirst"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is True
                for kw in node.keywords
            )
        ):
            idempotent.add(id(func.value))
    bad: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if id(node) in idempotent:
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name not in {"Enum", "ENUM"}:
            continue
        keywords = {
            kw.arg: ast.unparse(kw.value) if hasattr(ast, "unparse") else ""
            for kw in node.keywords
        }
        if "name" not in keywords:
            # Unnamed enums never become a PG native type; nothing to guard.
            continue
        create_type = keywords.get("create_type", "True")
        if create_type != "False":
            bad.append(f"{path.name}:{node.lineno}")
    return bad


def test_no_unconditional_enum_create_type() -> None:
    """No migration emits an unconditional CREATE TYPE on PostgreSQL."""
    versions = BACKEND_DIR / "migrations" / "versions"
    offenders: list[str] = []
    for path in sorted(versions.glob("*.py")):
        offenders.extend(_enum_calls_without_checkfirst(path))
    check(
        "no named Enum without create_type=False in migrations/versions",
        not offenders,
        f"unconditional CREATE TYPE at: {', '.join(offenders)}" if offenders else "",
    )


def _bool_cols_with_int_default(path: Path) -> list[str]:
    """Boolean columns whose server_default is an int-like literal.

    PostgreSQL rejects ``DEFAULT 0``/``DEFAULT 1`` for a boolean column
    (``column is of type boolean but default expression is of type
    integer``) while SQLite silently coerces it, so the defect only
    surfaces on the PG proof. The approved spellings are ``sa.false()`` /
    ``sa.true()`` (or ``sa.text("false")`` / ``sa.text("true")``), which
    render ``DEFAULT false`` / ``DEFAULT true`` on PG and stay
    behavior-neutral on SQLite.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    bad: list[str] = []

    def _is_int_like(node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return node.value in (0, 1, "0", "1")
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name == "text" and len(node.args) == 1:
                arg = node.args[0]
                return isinstance(arg, ast.Constant) and arg.value in (
                    0,
                    1,
                    "0",
                    "1",
                )
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name != "Column":
            continue
        has_bool = any(
            (isinstance(a, ast.Attribute) and a.attr == "Boolean")
            or (isinstance(a, ast.Name) and a.id == "Boolean")
            or (
                isinstance(a, ast.Call)
                and (
                    (isinstance(a.func, ast.Attribute) and a.func.attr == "Boolean")
                    or (isinstance(a.func, ast.Name) and a.func.id == "Boolean")
                )
            )
            for a in node.args
        )
        if not has_bool:
            continue
        for kw in node.keywords:
            if kw.arg == "server_default" and _is_int_like(kw.value):
                try:
                    rendered = ast.unparse(kw.value)
                except Exception:
                    rendered = "<default>"
                bad.append(f"{path.name}:{node.lineno} ({rendered})")
    return bad


def test_no_boolean_int_server_default() -> None:
    """No Boolean column defaults to an integer literal in versions/*."""
    versions = BACKEND_DIR / "migrations" / "versions"
    offenders: list[str] = []
    for path in sorted(versions.glob("*.py")):
        offenders.extend(_bool_cols_with_int_default(path))
    check(
        "no Boolean server_default with integer/string-int default in migrations/versions",
        not offenders,
        f"int-like boolean default at: {', '.join(offenders)}" if offenders else "",
    )


def _bare_like_without_cast(path: Path) -> list[str]:
    """``.like()``/``.ilike()`` calls in one file not wrapped in ``cast()``.

    On PostgreSQL a reflected native-enum column is a ``String`` subclass,
    so ``<enum-col>.like(...)`` renders ``<enumtype> ~~ unknown`` and PG
    raises ``UndefinedFunction`` (SQLite compares it as text). The approved
    spelling is ``cast(column, Text).like(...)`` — portable ``CAST()``,
    never the PG-only ``::`` operator — which is behavior-neutral on
    SQLite. String-literal SQL (e.g. an Oracle-only ``REGEXP_LIKE`` check
    constraint) is not a method call and is never flagged.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    bad: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute) and func.attr in ("like", "ilike")
        ):
            continue
        receiver = func.value
        if isinstance(receiver, ast.Call):
            recv_func = receiver.func
            recv_name = ""
            if isinstance(recv_func, ast.Attribute):
                recv_name = recv_func.attr
            elif isinstance(recv_func, ast.Name):
                recv_name = recv_func.id
            if recv_name == "cast":
                continue
        bad.append(f"{path.name}:{node.lineno}")
    return bad


def test_no_bare_like_without_cast() -> None:
    """No bare ``.like()``/``.ilike()`` without ``cast()`` in versions/*."""
    versions = BACKEND_DIR / "migrations" / "versions"
    offenders: list[str] = []
    for path in sorted(versions.glob("*.py")):
        offenders.extend(_bare_like_without_cast(path))
    check(
        "no bare .like()/.ilike() without cast() in migrations/versions",
        not offenders,
        f"bare LIKE without CAST at: {', '.join(offenders)}" if offenders else "",
    )


def test_append_only_trigger_branches_on_dialect() -> None:
    """install/remove_append_only have a PostgreSQL branch (gate A: 0022)."""
    path = BACKEND_DIR / "app" / "core" / "audit_chain.py"
    try:
        source = path.read_text()
    except OSError as exc:
        check("append-only trigger helper branches on dialect", False, str(exc))
        return
    problems: list[str] = []
    if '"postgresql"' not in source and "'postgresql'" not in source:
        problems.append("no postgresql dialect branch")
    for marker in (
        "RAISE EXCEPTION",
        "EXECUTE FUNCTION",
        "DROP TRIGGER IF EXISTS",
        "DROP FUNCTION IF EXISTS",
        "CREATE OR REPLACE FUNCTION",
    ):
        if marker not in source:
            problems.append(f"missing PG marker: {marker}")
    if "RAISE(ABORT" not in source:
        problems.append("sqlite RAISE(ABORT) path altered")
    if "CREATE TRIGGER IF NOT EXISTS" not in source:
        problems.append("sqlite CREATE TRIGGER IF NOT EXISTS path altered")
    if "CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE" in source:
        pass  # sqlite path byte-identical guard lives in the audit suites
    check(
        "append-only trigger helper branches on dialect (sqlite + pg)",
        not problems,
        "; ".join(problems),
    )


def _pg_url() -> str | None:
    return os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("PG_PROOF_URL")


def _pg_reachable(url: str) -> bool:
    try:
        import sqlalchemy as sa

        engine = sa.create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        engine.dispose()
        return True
    except Exception as exc:  # Missing driver/server is a skip, never a fail.
        print(f"    (pg probe: {exc})")
        return False


def test_pg_upgrade_head_when_available() -> None:
    """Scratch PostgreSQL reaches head (gated: skips without PG)."""
    url = _pg_url()
    if not url or not url.startswith("postgresql"):
        skip(
            "pg upgrade head",
            "no ALEMBIC_DATABASE_URL/PG_PROOF_URL postgresql URL in env",
        )
        return
    if not _pg_reachable(url):
        skip("pg upgrade head", "postgresql URL not reachable")
        return
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env["ALEMBIC_DATABASE_URL"] = url
    with tempfile.TemporaryDirectory(prefix="pg-enum-proof-") as tmp:
        marker = Path(tmp) / "marker"
        marker.write_text(url)
        result = subprocess.run(
            [sys.executable, "-m", "scripts.migrate", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
    tail = (result.stdout + result.stderr)[-1500:]
    check("pg upgrade head exits 0", result.returncode == 0, tail)


def main() -> int:
    print("pg enum checkfirst suite")
    test_no_unconditional_enum_create_type()
    test_no_boolean_int_server_default()
    test_no_bare_like_without_cast()
    test_append_only_trigger_branches_on_dialect()
    test_pg_upgrade_head_when_available()
    print(
        f"\n{RESULTS['pass']} passed, {RESULTS['fail']} failed, "
        f"{RESULTS['skip']} skipped"
    )
    for name, detail in FAILURES:
        print(f"FAILED: {name}\n{detail}")
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
