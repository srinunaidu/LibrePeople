"""The paged-collection envelope the contract declares.

`contracts/openapi/_components.yaml` defines `PaginatedResponse` as an object
with `items` and a `meta` object carrying `page`, `page_size`, `total` and
`total_pages`. This module is the Python side of that shape, so a new paged
endpoint does not invent its own field names.

Why a separate `meta` object rather than flat fields
----------------------------------------------------
The contract publishes the nested form. A flat response is a different
interface: a client generated from the contract reads `response.meta.total`,
and a screen written against a flat body reads `response.total`. This project
has already paid for that class of drift once (`D-040`); the envelope lives in
one place so the next endpoint inherits the declared shape.
"""
from __future__ import annotations

from pydantic import BaseModel


class PageMeta(BaseModel):
    """Where a page sits in its collection."""

    #: 1-based page that was returned.
    page: int
    #: Rows per page the server applied.
    page_size: int
    #: Rows matching the filter across every page.
    total: int
    #: Pages available at this page size. Zero for an empty collection.
    total_pages: int


def page_meta(total: int, page: int, page_size: int) -> PageMeta:
    """Build the envelope's `meta` for a count and a window."""
    return PageMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )
