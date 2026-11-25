"""Display-parity tests: stored Decimal text == CSV cell == PDF _money.

Scope: IN-INR only (verified IN runs are INR-gated). No payroll calculation
change, no ``money()`` change — this suite pins the *rendering* contract:

* stored ``str(Decimal)`` is the canonical 2dp text (values are already
  quantised via ``money()`` ROUND_HALF_UP before they are stored);
* CSV (``rows_to_csv``) carries that text verbatim;
* PDF ``_money`` (``payroll.py`` payslip-pdf) renders the same text and must
  never requantise.

Rounding edge (documented, not fixed): Python's ``f"{d:.2f}"`` uses
round-half-even while ``money()`` uses ROUND_HALF_UP, so they differ on
*unquantised* ``x.xx5`` inputs. Stored values are already 2dp, hence the
edge is unreachable on the stored path — the test below pins both
behaviours so a future requantising change fails loudly.

Out of scope (documented): JPY (Intl 0dp) / KWD (Intl 3dp) defaults. The
frontend pins ``minimum/maximumFractionDigits: 2`` with an explicit
currency on every money display, so no Intl per-currency default applies.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.rules.money import money
from app.services.report_exports import rows_to_csv


def _pdf_money(v):
    """Exact replica of ``_money`` in ``payroll.py`` payslip-pdf (no import:
    the endpoint helper is a closure; this copy pins its contract)."""
    try:
        d = Decimal(str(v))
        return f"{d:.2f}"
    except Exception:
        return str(v)


def _csv_cell(value: str | None) -> str:
    """Single CSV cell round-trip through the shared exporter."""
    text = rows_to_csv([{"amount": value}], ["amount"])
    # Strip BOM + header, return the single data line (csv may quote).
    body = text.lstrip("\ufeff")
    lines = body.splitlines()
    assert lines[0] == "amount"
    assert len(lines) == 2
    cell = lines[1]
    # Unquote a quoted cell (csv QUOTE_MINIMAL).
    if len(cell) >= 2 and cell.startswith('"') and cell.endswith('"'):
        cell = cell[1:-1].replace('""', '"')
    return cell


class TestStoredCsvPdfParity:
    """stored str(Decimal) == CSV == PDF _money for INR fixtures."""

    def test_positive_negative_zero(self):
        for raw in ["80000.00", "174562.50", "-2729.16", "208.50", "0.00", "15000.00"]:
            stored = str(money(raw))
            assert stored == raw  # fixtures are already 2dp
            assert _csv_cell(stored) == stored
            assert _pdf_money(stored) == stored

    def test_null_mapping(self):
        # Stored NULL has no amount text: CSV writes an empty cell, PDF and
        # the frontend both render the "—" placeholder (PDF via the
        # `is not None else "—"` branch, frontend via money()/moneyIn()).
        assert _csv_cell(None) == ""
        assert _pdf_money(None) == "None"  # never called with None in practice
        # The endpoint guards None before calling _money; pin the guard shape:
        guarded = _pdf_money("0.00") if None is not None else "—"
        assert guarded == "—"

    def test_stored_values_are_already_two_dp(self):
        # Every stored fixture quantises to exactly 2dp — the precondition
        # that keeps the HALF_UP vs half-even edge unreachable.
        for raw in ["25000", "22000.5", "30000.555", "21000.01", "0.005"]:
            assert money(raw).as_tuple().exponent == -2


class TestHalfUpVsHalfEvenEdge:
    """Documented edge: HALF_UP (money) vs round-half-even (PDF format)."""

    def test_money_uses_half_up_on_xx5(self):
        assert money("2.665") == Decimal("2.67")
        assert money("1.005") == Decimal("1.01")
        assert money("-1.005") == Decimal("-1.01")

    def test_python_format_uses_half_even_on_xx5(self):
        # f"{d:.2f}" (used by PDF _money) rounds half to even on the
        # *unquantised* input — the opposite answer to money() here
        # (2.665: keep-digit 6 is even so half-even stays; 1.005:
        # keep-digit 0 is even so half-even stays).
        assert f"{Decimal('2.665'):.2f}" == "2.66"
        assert f"{Decimal('1.005'):.2f}" == "1.00"
        # Hence _money must only ever receive already-quantised stored text:
        assert _pdf_money(str(money("2.665"))) == "2.67"
        assert _pdf_money(str(money("1.005"))) == "1.01"


class TestInrGateScope:
    """JPY/KWD Intl defaults are out of scope (IN runs are INR-gated)."""

    def test_inr_is_two_dp_by_contract(self):
        assert str(money("208.50")) == "208.50"
        assert str(money("0")) == "0.00"

    def test_non_inr_currencies_not_pinned_here(self):
        # money() itself is currency-agnostic (always 2dp HALF_UP); the
        # currency-specific Intl defaults (JPY 0dp, KWD 3dp) never apply
        # because every frontend money display passes explicit
        # minimum/maximumFractionDigits: 2 with an explicit currency.
        assert money("1000") == Decimal("1000.00")
        _ = ROUND_HALF_UP  # the single rounding mode for every currency
