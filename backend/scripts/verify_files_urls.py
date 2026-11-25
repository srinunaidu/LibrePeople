"""Verification script for the item 9 files-URL rewrite (LibrePeople).

Reports every value still stored under the old unauthenticated ``/files/``
prefix; exits non-zero while any remain (use ``--expect-legacy`` when
checking that a deliberate downgrade left them in place).

Run:
    DATABASE_URL=sqlite:///path/to/db python scripts/verify_files_urls.py
    python scripts/verify_files_urls.py --database-url sqlite:////path/to/db
"""

from __future__ import annotations

import argparse
import os
import sys

# Make the script runnable from anywhere: ``python scripts/verify_files_urls.py``.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "lp-files-verify-script-secret-0123456789")

from sqlalchemy import create_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.storage.url_rewrite import OLD_PREFIX, count_legacy_files_urls  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify stored /files/ URLs are rewritten.")
    parser.add_argument(
        "--database-url",
        default=None,
        help="DATABASE_URL to inspect; defaults to the configured settings value.",
    )
    parser.add_argument(
        "--expect-legacy",
        action="store_true",
        help="exit 0 when legacy values are present (e.g. after a deliberate downgrade).",
    )
    args = parser.parse_args()

    url = args.database_url or settings.DATABASE_URL or os.environ.get("DATABASE_URL", "")
    if not url:
        print("verify_files_urls: no DATABASE_URL configured", file=sys.stderr)
        return 2
    legacy = count_legacy_files_urls(create_engine(url))
    for report in legacy:
        print(
            f"LEGACY  {report['table']}.{report['column']}: "
            f"{report['rows']} row(s) still under {OLD_PREFIX}"
        )
    if not legacy:
        print("VERIFIED  no stored values still use the unauthenticated /files/ prefix")
    return 0 if (legacy and args.expect_legacy) or not legacy else 1


if __name__ == "__main__":
    sys.exit(main())
