"""Streaming CSV reader.

RFC 4180
--------
The reader follows RFC 4180: fields are separated by commas, records are
separated by CRLF (LF and CR are also accepted, because a file written on a
different platform is still a valid file), a field may be quoted with double
quotes, and a quoted field may contain commas, CRLF and doubled quotes.

The parser is *streaming*. It reads the file in chunks and yields one record
at a time; it never materialises the whole file as a string and never
materialises the whole file as a list of records. That is what keeps a
10,000-row import inside the 512 MB free-tier memory budget — the file is
the only thing that grows, and it grows on disk, not on the heap.

Limits
------
Two limits are enforced while reading, not after:

* the byte limit (5 MB by default) is checked as bytes are read, so an
  oversized upload is refused without ever being fully buffered;
* the row limit (10,000 by default) is checked as records are produced.

Both are configurable. Exceeding either raises :class:`ImportLimitError`,
which the endpoint turns into a 413 or a 422 — the file is refused as a
whole, because the operator's next action is to produce a smaller file, not
to read a list of bad rows.
"""
from __future__ import annotations

import csv
import io
import sys
from typing import Iterable, Iterator

from app.imports.errors import ErrorCode, ImportLimitError

#: The largest single field the parser will accept, in characters.
#: A field larger than this is refused rather than allowed to consume the
#: memory budget.
MAX_FIELD_CHARS = 1_000_000


class _ByteLimitReader(io.RawIOBase):
    """A binary reader that refuses to read past a byte limit.

    The limit is checked *during* the read, so a file that is far larger
    than the limit is abandoned after the first chunk that crosses it. The
    reader reads at most one byte beyond the limit, which is enough to know
    that the limit has been passed without buffering the rest of the file.
    """

    def __init__(self, stream, max_bytes: int) -> None:
        super().__init__()
        self._stream = stream
        self._max_bytes = max_bytes
        self.bytes_read = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:  # type: ignore[override]
        if self._max_bytes:
            remaining = self._max_bytes - self.bytes_read
            if remaining < 0:
                raise ImportLimitError(
                    ErrorCode.FILE_TOO_LARGE,
                    "The file is larger than the maximum upload size.",
                    max_bytes=self._max_bytes,
                )
            to_read = min(len(buffer), remaining + 1)
        else:
            to_read = len(buffer)
        chunk = self._stream.read(to_read)
        length = len(chunk)
        buffer[:length] = chunk
        self.bytes_read += length
        if self._max_bytes and self.bytes_read > self._max_bytes:
            raise ImportLimitError(
                ErrorCode.FILE_TOO_LARGE,
                "The file is larger than the maximum upload size.",
                max_bytes=self._max_bytes,
            )
        return length


def _configure_field_limit() -> int:
    """Set and return the csv module's field size limit."""
    previous = csv.field_size_limit()
    try:
        csv.field_size_limit(MAX_FIELD_CHARS)
    except OverflowError:  # pragma: no cover - platform dependent
        csv.field_size_limit(sys.maxsize)
    return previous


def _record_reader(stream, max_bytes: int):
    """Wrap a binary stream in a csv reader that enforces the limits."""
    limited = _ByteLimitReader(stream, max_bytes)
    previous = _configure_field_limit()
    try:
        buffered = io.BufferedReader(limited)
        text = io.TextIOWrapper(
            buffered,
            encoding="utf-8-sig",
            errors="strict",
            newline="",
        )
    except Exception:  # pragma: no cover - defensive
        csv.field_size_limit(previous)
        raise
    return _CsvReader(text, limited, previous)


class _CsvReader:
    """A thin wrapper that turns csv errors into import limit errors."""

    def __init__(self, text, limited, previous_limit: int) -> None:
        self._text = text
        self._limited = limited
        self._previous_limit = previous_limit
        self._reader = csv.reader(text, strict=True)

    @property
    def bytes_read(self) -> int:
        return self._limited.bytes_read

    def __iter__(self) -> Iterator[list[str]]:
        return self

    def __next__(self) -> list[str]:
        try:
            return next(self._reader)
        except csv.Error as exc:
            raise ImportLimitError(
                ErrorCode.MALFORMED_CSV,
                "The file is not valid CSV: " + str(exc),
            ) from None
        except UnicodeDecodeError:
            raise ImportLimitError(
                ErrorCode.NOT_UTF8,
                "The file is not valid UTF-8.",
            ) from None

    def close(self) -> None:
        csv.field_size_limit(self._previous_limit)


def iter_records(
    stream,
    max_bytes: int,
    max_rows: int,
) -> Iterator[tuple[int, list[str]]]:
    """Yield ``(row_number, record)`` for every record, the header included.

    ``row_number`` counts records, with the header as row 1, so the first
    data row is row 2. This is the number the operator sees in a
    spreadsheet when the file has no embedded newlines, which is the normal
    case; a file with a newline inside a quoted field shifts the physical
    line numbers but not these, which is why the row number is the record
    number.

    The row limit counts *data* rows. The header is not a row.

    The reader is closed when the generator is exhausted or discarded.
    """
    reader = _record_reader(stream, max_bytes)
    try:
        data_rows = 0
        for index, record in enumerate(reader):
            if index > 0:
                data_rows += 1
                if max_rows and data_rows > max_rows:
                    raise ImportLimitError(
                        ErrorCode.TOO_MANY_ROWS,
                        f"The file has more than {max_rows} data rows.",
                        max_rows=max_rows,
                    )
            yield index + 1, record
    finally:
        reader.close()


def read_all_limited(stream, max_bytes: int) -> bytes:
    """Read a binary stream into memory, refusing to exceed ``max_bytes``.

    The read is chunked so that an oversized upload is detected without
    buffering all of it.
    """
    buffer = io.BytesIO()
    total = 0
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if max_bytes and total > max_bytes:
            raise ImportLimitError(
                ErrorCode.FILE_TOO_LARGE,
                "The file is larger than the maximum upload size.",
                max_bytes=max_bytes,
            )
        buffer.write(chunk)
    return buffer.getvalue()
