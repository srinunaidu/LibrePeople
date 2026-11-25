"""Tabular export builders for workforce reports (LP-REP-002).

CSV is built with the standard library. XLSX is built as minimal Office Open
XML with inline strings (zipfile + xml), so the reports endpoints serve a
real ``.xlsx`` without adding a dependency. No payroll engine call, no
recomputation: callers pass rows already read from stored facts.
"""
from __future__ import annotations

import csv
import io
import zipfile
from xml.sax.saxutils import escape

#: Byte-order mark starting every CSV this module builds. Excel on Windows
#: only detects UTF-8 when the BOM is present; without it non-ASCII names
#: (e.g. Indian-language employee names) decode as mojibake.
CSV_BOM = "\ufeff"


def rows_to_csv(rows: list[dict], columns: list[str]) -> str:
    """Render rows as CSV text starting with the UTF-8 BOM.

    CSV INVARIANT: the returned text ALWAYS begins with U+FEFF
    (:data:`CSV_BOM`) followed by the header row. Decode with ``utf-8-sig``
    (which strips the BOM) to recover the plain header-first text; decoding
    with plain ``utf-8`` leaves the BOM as the first character of the
    header name. The invariant holds for every report and every role —
    masking changes cell values, never the framing.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c) for c in columns})
    return CSV_BOM + buffer.getvalue()


def _sheet_xml(rows: list[dict], columns: list[str]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    # Header row.
    parts.append("<row r=\"1\">")
    for col in columns:
        parts.append(f"<c t=\"inlineStr\"><is><t>{escape(col)}</t></is></c>")
    parts.append("</row>")
    for i, row in enumerate(rows, start=2):
        parts.append(f"<row r=\"{i}\">")
        for col in columns:
            value = row.get(col)
            cell = "" if value is None else str(value)
            parts.append(f"<c t=\"inlineStr\"><is><t>{escape(cell)}</t></is></c>")
        parts.append("</row>")
    parts.append("</sheetData>")
    parts.append("</worksheet>")
    return "".join(parts)


def rows_to_xlsx(rows: list[dict], columns: list[str], sheet: str = "Report") -> bytes:
    """Minimal but valid XLSX: one worksheet with inline strings."""
    safe_sheet = escape(sheet or "Report")
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.open-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
    workbook = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{safe_sheet}" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows, columns))
    return buffer.getvalue()


def mask_movement_row(row: dict, role: str | None) -> dict:
    """Mask bank/tax identifiers in a workforce-movement row for ``role``.

    Movement rows never carry raw Aadhaar; PAN/IFSC-style fields are nulled
    for roles outside the central bank/tax policy.
    """
    from app.core.sensitive_fields import mask_bank_tax

    return mask_bank_tax(row, role)


def mask_payroll_row(row: dict, role: str | None) -> dict:
    """Mask a stored-payslip row: bank/tax policy + Aadhaar never raw."""
    from app.core.sensitive_fields import mask_bank_tax

    out = mask_bank_tax(row, role)
    aadhaar = out.pop("aadhaar_number", None)
    if aadhaar:
        text = str(aadhaar)
        out["aadhaar"] = f"****-****-{text[-4:]}" if len(text) >= 4 else "****"
    else:
        out["aadhaar"] = None
    return out
