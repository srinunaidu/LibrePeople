"""Offer letter generation (PDF) using fpdf2.

The salary unit
---------------
``base_salary`` is the amount paid for **one pay period**. It is not an
annual figure, and the letter must not describe it as one.

The previous wording said "Your annual compensation for this role will be
...". That is wrong twice over: the number is per period, and a reader who
takes it as an annual figure will believe they have been offered twelve
times what they will actually receive. This is audit finding A2-16, and the
per-period unit is the owner-confirmed decision recorded in
`agents/DECISIONS.md`.

A letter that states a per-period amount without saying so is still wrong,
so the wording says "for each pay period" and names the frequency the
letter was written for. The frequency comes from the payroll profile when
there is one, and otherwise reads "each pay period", which is true whatever
the frequency is.
"""
from __future__ import annotations

from datetime import date


#: How a pay frequency is written in a sentence.
_FREQUENCY_WORDS = {
    "monthly": "each month",
    "biweekly": "each fortnight",
    "bi-weekly": "each fortnight",
    "weekly": "each week",
    "quarterly": "each quarter",
    "annual": "each year",
    "yearly": "each year",
}


def default_pay_frequency() -> str:
    """The platform's default pay frequency.

    It is read from the pay profile model rather than repeated here, so
    that the letter and the payroll engine cannot drift apart. If the
    model cannot be read, the platform default is used.
    """
    try:
        from app.models.payroll import EmployeePayProfile

        default = EmployeePayProfile.__table__.c.pay_frequency.default
        value = getattr(default, "arg", None)
        if value:
            return str(value)
    except Exception:  # noqa: BLE001
        pass
    return "Monthly"


def _period_phrase(pay_frequency: str | None) -> str:
    """The phrase that says how often the amount is paid."""
    frequency = pay_frequency or default_pay_frequency()
    key = str(frequency).strip().lower()
    return _FREQUENCY_WORDS.get(key, f"each {key} pay period")


def render_offer_letter(
    *,
    candidate_name: str,
    job_title: str,
    department_name: str,
    salary: float | None,
    start_date: date,
    offer_date: date,
    offer_number: str,
    company_name: str = "Karmathy",
    pay_frequency: str | None = None,
) -> bytes:
    """Return a simple, professional offer letter as PDF bytes."""
    from fpdf import FPDF  # lazy import so the app runs without fpdf2 installed

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, company_name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"Offer Reference: {offer_number}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Date
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, offer_date.strftime("%d %B %Y"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Salutation
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Dear {candidate_name},", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Body
    pdf.set_font("Helvetica", "", 11)
    body = (
        f"We are delighted to offer you the position of {job_title} in the "
        f"{department_name} department at {company_name}. Your expected start "
        f"date is {start_date.strftime('%d %B %Y')}."
    )
    pdf.multi_cell(0, 7, body)
    pdf.ln(3)

    if salary is not None:
        # The amount is per pay period. Saying so is not a formality: a
        # candidate who reads a per-period figure as an annual figure has
        # been offered a twelfth of what they will be paid, and that is a
        # dispute waiting to happen.
        period = _period_phrase(pay_frequency)
        comp = (
            f"Your pay for this role will be {salary:,.2f} for {period}. "
            f"This figure is the amount payable for one pay period, not an "
            f"annual figure. It is subject to applicable statutory "
            f"deductions and company policy."
        )
        pdf.multi_cell(0, 7, comp)
        pdf.ln(3)

    terms = (
        "This offer is contingent upon successful completion of background "
        "verification and submission of the required onboarding documents. "
        "Please confirm your acceptance by signing and returning a copy of "
        "this letter."
    )
    pdf.multi_cell(0, 7, terms)
    pdf.ln(8)

    pdf.cell(0, 7, "We look forward to welcoming you to the team.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Sincerely,", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"People & Culture Team, {company_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(14)

    # Signature block
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Candidate acceptance:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.cell(80, 6, "Signature: ______________________", new_x="RIGHT", new_y="NEXT")
    pdf.cell(0, 6, "Date: ____________", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
