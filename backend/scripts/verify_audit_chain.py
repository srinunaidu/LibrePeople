#!/usr/bin/env python3
"""Verify the audit hash chain and report the first entry that fails.

Usage
-----
    python -m scripts.verify_audit_chain            # from backend/
    python -m scripts.verify_audit_chain --json     # machine-readable
    python -m scripts.verify_audit_chain --no-head  # ignore the recorded head

Exit codes
----------
``0``  every entry verifies and the head matches the last entry.
``1``  an entry does not verify, or entries are missing from the tail. The
       first failing entry id is named on stdout.
``2``  the chain could not be read (no database, or the chain columns are not
       there yet).

The head hash is printed on success. Record it somewhere outside the
database (a release ticket, a report, a second system): the chain detects an
edit or a removal, and anchoring the head is what makes a full rewrite
detectable too. See the canonical form in ``app/core/audit_chain.py``.
"""
from __future__ import annotations

import argparse
import json
import sys

from app.core.audit_chain import verify_chain
from app.core.database import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the audit hash chain")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as one JSON object",
    )
    parser.add_argument(
        "--no-head",
        action="store_true",
        help="walk the entries but do not compare the recorded head",
    )
    args = parser.parse_args(argv)

    try:
        with SessionLocal() as db:
            result = verify_chain(db, check_head=not args.no_head)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        print(
            f"audit chain: could not read the chain: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(result.as_dict(), sort_keys=True))
    else:
        if result.ok:
            print(result.message)
        else:
            print(result.message, file=sys.stderr)
            print(
                f"audit chain: {result.entries} entries verified before the failure",
                file=sys.stderr,
            )
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
