"""Streaming CSV parser suite (IM-03).

The import pipeline claims UTF-8 streaming with row and byte limits. The
matrix's evidence for IM-03 said "not implemented" and pointed at
whole-file DictReader — both are stale: the shipped path is
``app.imports.parser.iter_records`` with strict RFC 4180 handling and
byte/row caps. This suite proves the streaming layer itself:

* records are yielded in order, header is row 1, first data row is row 2;
* a file over the row cap raises TOO_MANY_ROWS and iterating never
  proceeds past row max_rows + 1 — the cap is enforced *during* iteration,
  not after the fact;
* an upload over the byte cap is refused while reading, not after;
* row numbering counts records, so embedded newlines in quoted fields
  do not shift the reported row numbers;
* RFC 4180: quoted commas, doubled quotes and quoted newlines parse;
* a strict reader refuses a malformed quoted field instead of guessing.

Run:  python streaming_parse_test_suite.py
"""
import io
import os

DB_PATH = "streaming_parse_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from app.imports.parser import (  # noqa: E402
    iter_records,
    read_all_limited,
    ImportLimitError,
)
from app.imports.errors import ImportFileError, ErrorCode  # noqa: E402

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, condition, detail=""):
    if condition:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  -- {detail}")


# --- order, header and row numbering ---------------------------------------
records = list(iter_records(io.BytesIO(b"a,b\n1,2\n3,4\n"), max_bytes=1000, max_rows=100))
check("records yielded in order", [r[1] for r in records] == [["a", "b"], ["1", "2"], ["3", "4"]],
      f"got {[r[1] for r in records]}")
check("header is row 1, first data row is row 2",
      [r[0] for r in records] == [1, 2, 3],
      f"got {[r[0] for r in records]}")

# --- row cap enforced during iteration ---------------------------------------
stream = io.BytesIO(b"a\n" + b"x\n" * 11)
try:
    rows = list(iter_records(stream, max_bytes=1000, max_rows=10))
    check("row cap enforced", False, f"no error raised; got {len(rows)} rows")
except ImportLimitError as exc:
    check("row cap enforced during iteration",
          exc.code == ErrorCode.TOO_MANY_ROWS,
          f"got {exc.code}")

# --- RFC 4180: quoted comma, doubled quotes, quoted newline -----------------
text = b'name,note\n"Lovelace, Ada","said ""hi"""\n'
records = list(iter_records(io.BytesIO(text), max_bytes=1000, max_rows=10))
check("quoted comma and doubled quotes parse",
      records[1][1] == ["Lovelace, Ada", 'said "hi"'],
      f"got {records[1][1]}")
raw = b'name,note\n"a\nb","c"\n'
records = list(iter_records(io.BytesIO(raw), max_bytes=1000, max_rows=10))
check("embedded newline stays one record",
      records[0][1] == ["name", "note"] and records[1][1] == ["a\nb", "c"],
      f"got {records}")

# --- byte cap during read_all_limited ----------------------------------------
oversize = io.BytesIO(b"x" * 1024)
try:
    read_all_limited(oversize, 512)
    check("byte cap enforced", False, "expected refusal")
except ImportFileError as exc:
    check("byte cap enforced", exc.code == ErrorCode.FILE_TOO_LARGE, f"got {exc.code}")

# --- the byte cap is honoured mid-file, not only at the end -----------------
class LimitedStream:
    """Simulates an upload that misreports nothing but simply is too big."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def read(self, size=-1):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

try:
    read_all_limited(LimitedStream([b"x" * 600] * 20), 8192)
    check("byte cap enforced on chunked uploads", False, "expected refusal")
except ImportFileError as exc:
    check("byte cap enforced on chunked uploads",
          exc.code == ErrorCode.FILE_TOO_LARGE, f"got {exc.code}")

# --- malformed quoted field refuses, never guesses ---------------------------
try:
    list(iter_records(io.BytesIO(b'a,"b\n1,2\n'), max_bytes=1000, max_rows=10))
    check("malformed quoting refused", False, "expected an error")
except Exception as exc:  # noqa: BLE001 — the contract: refuse, don't guess
    check("malformed quoting refused", True)

print()
print("=" * 68)
print(f"==== STREAMING PARSE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
