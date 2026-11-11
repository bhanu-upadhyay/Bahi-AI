from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.models.invoice import Invoice, normalize_invoice_number
from app.models.purchase_order import PurchaseOrder

logger = logging.getLogger("bahi_ai.extraction")


def clean_amount(val_str: Optional[str]) -> Optional[Decimal]:
    """Safely converts currency string to Decimal without floating-point math.
    Strictly ignores percentage values (e.g. 18%, 9.00%) so tax rates are never
    mistaken for monetary amounts.
    """
    if not val_str:
        return None
    val_str = str(val_str).strip()
    if not val_str or "%" in val_str or "percent" in val_str.lower():
        return None

    # Remove currency symbols ($, €, £, ₹, Rs., etc.) and whitespace
    clean = re.sub(r"[^\d.,-]", "", val_str).strip()
    if not clean or clean == "-" or clean == ".":
        return None

    # Handle European format (1.234,56) vs US/Indian format (1,234.56 or 1,40,474.00)
    is_negative = clean.startswith("-")
    if is_negative:
        clean = clean[1:]

    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            # European format: 1.234,56 -> 1234.56
            clean = clean.replace(".", "").replace(",", ".")
        else:
            # US / Indian format: 1,234.56 or 1,40,474.00 -> 1234.56
            clean = clean.replace(",", "")
    elif "," in clean:
        parts = clean.split(",")
        if len(parts[-1]) == 2:
            clean = clean.replace(",", ".")
        else:
            clean = clean.replace(",", "")

    try:
        dec = Decimal(clean)
        if is_negative:
            dec = -dec
        return dec.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_date_string(date_str: Optional[str]) -> Optional[date]:
    """Extracts and parses dates from various regional formats including Indian
    DD-MM-YYYY, ISO YYYY-MM-DD, US MM/DD/YYYY, and verbose dates.
    Strips out trailing timestamps and parenthetical metadata (e.g. '( 01:45 PM )').
    """
    if not date_str:
        return None

    # 1. Regex search for standard DD-MM-YYYY or DD/MM/YYYY or MM/DD/YYYY
    d_match = re.search(r"\b([0-9]{1,2})[-/.]([0-9]{1,2})[-/.]([0-9]{4})\b", date_str)
    if d_match:
        p1, p2, year = int(d_match.group(1)), int(d_match.group(2)), int(d_match.group(3))
        # Disambiguate day vs month
        if p1 > 12:
            # Definitely DD-MM-YYYY
            day, month = p1, p2
        elif p2 > 12:
            # Definitely MM-DD-YYYY
            month, day = p1, p2
        else:
            # Default to DD-MM-YYYY for Indian / AP context
            day, month = p1, p2
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # 2. Regex search for ISO format YYYY-MM-DD
    iso_match = re.search(r"\b([0-9]{4})[-/.]([0-9]{1,2})[-/.]([0-9]{1,2})\b", date_str)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # 3. Regex search for textual dates like '15 Jan 2025' or 'January 15, 2025'
    text_date_match = re.search(
        r"\b([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})\b",
        date_str,
    )
    if text_date_match:
        clean_text = text_date_match.group(1).replace(",", "")
        formats = ["%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(clean_text, fmt).date()
            except ValueError:
                continue

    return None


def extract_currency(text: str) -> str:
    """Detects currency symbol or code from document text."""
    if "INR" in text or "₹" in text or "Rs" in text or "Rupees" in text:
        return "INR"
    if "EUR" in text or "€" in text:
        return "EUR"
    if "GBP" in text or "£" in text:
        return "GBP"
    if "USD" in text or "$" in text:
        return "USD"
    return "USD"


def match_registered_vendor(raw_text: str, db: Session) -> Tuple[Optional[Vendor], float]:
    """Matches text against registered university vendors in PostgreSQL."""
    try:
        vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
        normalized_text = raw_text.lower()

        # Check vendor code first (e.g. VND-TECH-01)
        for v in vendors:
            if v.vendor_code.lower() in normalized_text:
                return v, 0.98

        # Check tax identifier if present
        for v in vendors:
            if v.tax_identifier and v.tax_identifier.lower() in normalized_text:
                return v, 0.99

        # Check legal name
        for v in vendors:
            v_name = v.legal_name.lower().strip()
            if v_name in normalized_text:
                return v, 0.95
            words = [
                w
                for w in v_name.split()
                if len(w) > 3
                and w not in ["inc", "llc", "corp", "ltd", "solutions", "services", "company", "pvt"]
            ]
            if len(words) >= 2 and " ".join(words[:2]) in normalized_text:
                return v, 0.85

        return None, 0.0
    except Exception as e:
        logger.warning(f"Error matching vendor against database: {e}")
        return None, 0.0


def extract_gstins(raw_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts Indian GSTINs and separates Supplier GSTIN from Customer GSTIN.
    Supplier GSTIN appears in header/supplier area; Customer GSTIN appears in Billed To section.
    Standard GSTIN format: 2 digits (state code) + 5 letters (PAN) + 4 digits + 1 letter + 1 char + Z + 1 char.
    """
    gstin_pattern = r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1})\b"
    all_gstins = re.findall(gstin_pattern, raw_text)

    supplier_gstin = None
    customer_gstin = None

    if all_gstins:
        # Check if customer section exists
        billed_match = re.search(r"(?i)\b(?:billed\s*to|bill\s*to|customer|buyer|party\s*name)\b", raw_text)
        if billed_match:
            billed_pos = billed_match.start()
            # GSTINs before 'Billed to' belong to supplier
            supp_matches = [g for g in re.finditer(gstin_pattern, raw_text) if g.start() < billed_pos]
            cust_matches = [g for g in re.finditer(gstin_pattern, raw_text) if g.start() >= billed_pos]

            supplier_gstin = supp_matches[0].group(1) if supp_matches else None
            customer_gstin = cust_matches[0].group(1) if cust_matches else None

        if not supplier_gstin and len(all_gstins) > 0:
            supplier_gstin = all_gstins[0]
        if not customer_gstin and len(all_gstins) > 1:
            customer_gstin = all_gstins[1]

    return supplier_gstin, customer_gstin


def extract_customer_name(raw_text: str) -> Optional[str]:
    """Extracts customer or billed-to entity name from the invoice."""
    patterns = [
        r"(?i)(?:billed\s*to|bill\s*to|customer|buyer|party\s*name|invoice\s*to)[:.\s]+(?:m/s\.?\s*)?([^\n\r,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, raw_text)
        if m:
            cand = m.group(1).strip()
            # Clean up trailing label remnants
            cand = re.sub(r"(?i)\b(?:address|gstin|pan|state)\b.*", "", cand).strip()
            if len(cand) > 2:
                return cand
    return None


def extract_vendor_name(
    raw_text: str, lines: List[str], db: Session
) -> Tuple[Optional[str], Optional[int], Optional[str], float]:
    """Identifies the vendor / supplier name from registered database records,
    invoice header layout, and bottom signature blocks. Never mistakes GSTIN,
    PAN, phone numbers, email addresses, or postal addresses for the vendor.
    """
    # 1. Registered Vendor Match from Database
    matched_vendor, vendor_conf = match_registered_vendor(raw_text, db)
    if matched_vendor:
        return matched_vendor.legal_name, matched_vendor.id, matched_vendor.vendor_code, vendor_conf

    # 2. Corroborate with Bottom Signatory / Authorised Signatory block
    for_vendor = None
    for_match = re.search(
        r"(?i)\bFor\s+([A-Za-z0-9\s.,&-]+?)(?:\r?\n|Receiver|Authorised|Authorized|$)",
        raw_text,
    )
    if for_match:
        cand = for_match.group(1).strip()
        if len(cand) > 3 and not re.search(r"(?i)^(?:the|payment|details|goods)\b", cand):
            for_vendor = cand

    # 3. Header Block Extraction
    # Locate where header ends (usually at 'Billed to', 'Invoice No', 'Dated')
    header_end_idx = len(lines)
    for idx, line in enumerate(lines):
        if re.search(
            r"(?i)\b(?:billed\s*to|bill\s*to|customer|invoice\s*no|invoice\s*number|dated|date\s*:|buyer|consignee)\b",
            line,
        ):
            header_end_idx = idx
            break

    header_lines = lines[: max(header_end_idx, 1)]
    header_candidate = None

    for line in header_lines:
        line_clean = line.strip()
        if len(line_clean) < 3:
            continue
        # Skip doc title labels
        if re.search(
            r"(?i)^(?:gstin|pan|cin|tax\s*invoice|original\s*copy|invoice|bill\s*of\s*supply|cash\s*memo|delivery\s*challan|duplicate\s*copy)\b",
            line_clean,
        ):
            continue
        # Skip contact / web info
        if re.search(r"(?i)(?:tel|phone|mobile|email|contact|fax|www|\.in|\.com|@|http)", line_clean):
            continue
        # Skip address lines
        if re.search(
            r"(?i)\b(?:road|street|marg|nagar|floor|mall|complex|building|lane|avenue|sector|phase|b-\d+|near|opp|opposite|plot|pin|district|state|place\s*of\s*supply)\b",
            line_clean,
        ):
            continue
        if re.search(r"\b\d{6}\b", line_clean):
            continue

        header_candidate = line_clean
        break

    # If both header candidate and signature match, high confidence
    if header_candidate and for_vendor:
        if (
            header_candidate.lower() in for_vendor.lower()
            or for_vendor.lower() in header_candidate.lower()
        ):
            return for_vendor, None, None, 0.92

    if for_vendor:
        return for_vendor, None, None, 0.88

    if header_candidate:
        return header_candidate, None, None, 0.75

    return None, None, None, 0.0


def extract_financial_fields(raw_text: str, lines: List[str]) -> Dict[str, Any]:
    """Extracts subtotal (taxable amount), taxes (CGST, SGST, IGST, total tax),
    discounts, round-off, and grand total. Performs strict Decimal reconciliation
    and provides status flags for accounting audit.
    """
    subtotal: Optional[Decimal] = None
    grand_total: Optional[Decimal] = None
    cgst: Optional[Decimal] = None
    sgst: Optional[Decimal] = None
    igst: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    roundoff: Optional[Decimal] = None

    # --- 1. Check for tabular summary format (e.g. GST summary table) ---
    for i, line in enumerate(lines):
        if re.match(r"(?i)^totals?$", line):
            # Check next 4 numeric lines: [Taxable Amt, CGST, SGST, Total Tax]
            if i + 4 < len(lines):
                v1 = clean_amount(lines[i + 1])
                v2 = clean_amount(lines[i + 2])
                v3 = clean_amount(lines[i + 3])
                v4 = clean_amount(lines[i + 4])
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    # Verify math: v2 + v3 == v4
                    if abs((v2 + v3) - v4) <= Decimal("0.05"):
                        subtotal = v1
                        cgst = v2
                        sgst = v3
                        total_tax = v4
                        break
            # Check next 3 numeric lines: [Taxable Amt, IGST, Total Tax]
            if i + 3 < len(lines):
                v1 = clean_amount(lines[i + 1])
                v2 = clean_amount(lines[i + 2])
                v3 = clean_amount(lines[i + 3])
                if v1 is not None and v2 is not None and v3 is not None:
                    if abs(v2 - v3) <= Decimal("0.05"):
                        subtotal = v1
                        igst = v2
                        total_tax = v3
                        break

    # --- 2. Extract Grand Total / Invoice Total ---
    if grand_total is None:
        for i, line in enumerate(lines):
            if re.search(
                r"(?i)\b(?:grand\s*total|invoice\s*total|net\s*payable|amount\s*payable|total\s*payable|balance\s*due)\b",
                line,
            ):
                # Try inline
                m = re.search(r"[:.\s]+[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)", line)
                val = clean_amount(m.group(1)) if m else None
                # If not inline, look on next line
                if val is None and i + 1 < len(lines):
                    val = clean_amount(lines[i + 1])
                if val is not None and val > Decimal("0.00"):
                    grand_total = val
                    break

    if grand_total is None:
        gt_patterns = [
            r"(?i)(?:grand\s*total|invoice\s*total|net\s*payable|amount\s*payable|total\s*amount(?:\s*due)?|total\s*due|balance\s*due)\s*(?:\([^)]+\))?[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
            r"(?i)\btotal(?:\s+amount)*\s*(?:\([^)]+\))?[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)\b",
        ]
        for pat in gt_patterns:
            for m in re.finditer(pat, raw_text):
                val = clean_amount(m.group(1))
                if val is not None and val > Decimal("0.00"):
                    grand_total = val
                    break
            if grand_total is not None:
                break

    # --- 3. Extract Subtotal (Taxable Value) if not found in table ---
    if subtotal is None:
        for i, line in enumerate(lines):
            if re.search(
                r"(?i)\b(?:taxable\s*(?:amt|amount|value)|sub\s*total|subtotal|total\s*taxable|net\s*amount)\b",
                line,
            ):
                m = re.search(r"[:.\s]+[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)", line)
                val = clean_amount(m.group(1)) if m else None
                if val is None and i + 1 < len(lines):
                    nxt = lines[i + 1]
                    if not re.search(r"(?i)(?:cgst|sgst|igst|tax)", nxt):
                        val = clean_amount(nxt)
                if val is not None and val > Decimal("0.00"):
                    subtotal = val
                    break

    if subtotal is None:
        sub_patterns = [
            r"(?i)(?:taxable\s*(?:amount|value|amt\.?)|total\s*taxable\s*value|sub\s*total|subtotal|net\s*amount)\s*(?:\([^)]+\))?[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
        ]
        for pat in sub_patterns:
            m = re.search(pat, raw_text)
            if m:
                val = clean_amount(m.group(1))
                if val is not None and val > Decimal("0.00"):
                    subtotal = val
                    break

    # --- 4. Extract CGST, SGST, IGST if not found in table ---
    if cgst is None:
        cgst_m = re.search(r"(?i)\bCGST\b(?!\s*%)[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)", raw_text)
        if cgst_m:
            cgst = clean_amount(cgst_m.group(1))

    if sgst is None:
        sgst_m = re.search(r"(?i)\b(?:SGST|UTGST)\b(?!\s*%)[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)", raw_text)
        if sgst_m:
            sgst = clean_amount(sgst_m.group(1))

    if igst is None:
        igst_m = re.search(r"(?i)\bIGST\b(?!\s*%)[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)", raw_text)
        if igst_m:
            igst = clean_amount(igst_m.group(1))

    # --- 5. Extract Total Tax if not found in table ---
    if total_tax is None:
        if cgst is not None and sgst is not None:
            total_tax = cgst + sgst
        elif igst is not None:
            total_tax = igst
        else:
            tax_m = re.search(
                r"(?i)(?:total\s*tax|tax\s*amount|gst\s*amount|vat\s*amount)\b(?!\s*%)[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
                raw_text,
            )
            if tax_m:
                total_tax = clean_amount(tax_m.group(1))
            else:
                gen_tax = re.search(
                    r"(?i)\b(?:tax|vat|gst)\b(?!\s*%)[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
                    raw_text,
                )
                if gen_tax:
                    total_tax = clean_amount(gen_tax.group(1))

    # --- 6. Extract Round Off & Discounts ---
    round_m = re.search(
        r"(?i)(?:less\s*:\s*)?round(?:ed)?\s*off(?:\s*\([^)]+\))?[:.\s]*\n?[$€£₹]?\s*([+-]?[0-9,]+(?:\.[0-9]{2})?)",
        raw_text,
    )
    if round_m:
        roundoff = clean_amount(round_m.group(1))

    disc_m = re.search(
        r"(?i)(?:less\s*:\s*)?(?:trade\s*)?discount[:.\s]*\n?[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
        raw_text,
    )
    if disc_m:
        discount = clean_amount(disc_m.group(1))

    # --- 7. Strict Financial Reconciliation ---
    reconciled = False
    reconciliation_status = "UNVERIFIED"
    reconciliation_message = ""

    tax_val = total_tax if total_tax is not None else Decimal("0.00")
    disc_val = discount if discount is not None else Decimal("0.00")
    round_val = roundoff if roundoff is not None else Decimal("0.00")

    if subtotal is not None and grand_total is not None:
        expected = subtotal + tax_val - disc_val + round_val
        diff = abs(expected - grand_total)
        # Allow small tolerance for fractional rounding
        if diff <= Decimal("0.05") or (roundoff is None and diff <= Decimal("1.00")):
            reconciled = True
            reconciliation_status = "RECONCILED"
            reconciliation_message = (
                f"Reconciled: Subtotal ({subtotal}) + Tax ({tax_val})"
                + (f" - Discount ({disc_val})" if disc_val > 0 else "")
                + (f" + Rounding ({round_val})" if round_val != 0 else "")
                + f" = Total ({grand_total})"
            )
        else:
            reconciliation_status = "DISCREPANCY"
            reconciliation_message = (
                f"Discrepancy: Expected total ({expected}) != Invoiced total ({grand_total}) [Diff: {diff}]"
            )
    elif grand_total is not None and subtotal is not None and total_tax is None:
        if grand_total >= subtotal:
            total_tax = grand_total - subtotal
            reconciliation_status = "INFERRED"
            reconciliation_message = f"Inferred Tax Amount ({total_tax}) from Total - Subtotal"
    elif grand_total is not None and total_tax is not None and subtotal is None:
        if grand_total >= total_tax:
            subtotal = grand_total - total_tax
            reconciliation_status = "INFERRED"
            reconciliation_message = f"Inferred Subtotal ({subtotal}) from Total - Tax"
    elif subtotal is not None and total_tax is not None and grand_total is None:
        grand_total = subtotal + total_tax - disc_val + round_val
        reconciliation_status = "INFERRED"
        reconciliation_message = f"Inferred Grand Total ({grand_total}) from Subtotal + Tax"

    return {
        "subtotal": subtotal,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "tax_amount": total_tax,
        "total_amount": grand_total,
        "discount": discount,
        "roundoff": roundoff,
        "reconciled": reconciled,
        "reconciliation_status": reconciliation_status,
        "reconciliation_message": reconciliation_message,
    }


def extract_fields_from_text(raw_text: str, db: Session) -> Dict[str, Any]:
    """Performs comprehensive heuristic, regex, and database parsing on raw document
    text to extract the 11 specified invoice fields and calculate field-level confidences.
    """
    field_confidences: Dict[str, float] = {}
    missing_fields: List[str] = []

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    # 1. GSTIN & Tax Identifiers
    supplier_gstin, customer_gstin = extract_gstins(raw_text)
    tax_id = supplier_gstin
    tax_id_conf = 0.95 if supplier_gstin else 0.0

    if not tax_id:
        tax_m = re.search(
            r"(?i)(?:tax\s*(?:id|identifier|no)|ein|tin|vat\s*no)[:.\s]+([A-Za-z0-9-]+)",
            raw_text,
        )
        if tax_m:
            tax_id = tax_m.group(1).strip()
            tax_id_conf = 0.90

    field_confidences["tax_identifier"] = tax_id_conf

    # 2. Customer Name
    customer_name = extract_customer_name(raw_text)

    # 3. Vendor Extraction & Matching
    vendor_name, vendor_id, vendor_code, vendor_conf = extract_vendor_name(raw_text, lines, db)
    field_confidences["vendor_name"] = vendor_conf
    if not vendor_name or vendor_conf < 0.5:
        missing_fields.append("vendor")

    # 4. Invoice Number
    inv_num = None
    inv_conf = 0.0
    inv_patterns = [
        r"(?i)\b(?:invoice\s*(?:no|number|#|num|id)|bill\s*no|inv\s*no)[:.\s]*([A-Za-z0-9-_/]{2,30})\b",
        r"(?i)\b(INV-[A-Za-z0-9-_]+)\b",
        r"(?i)\bINVOICE\s*#\s*([A-Za-z0-9-_]+)\b",
    ]
    for pat in inv_patterns:
        m = re.search(pat, raw_text)
        if m:
            inv_num = m.group(1).strip()
            inv_conf = 0.95
            break

    if not inv_num:
        m = re.search(r"\b([A-Z]{2,4}-[0-9]{4}-[0-9]{3,6})\b", raw_text)
        if m:
            inv_num = m.group(1).strip()
            inv_conf = 0.70

    field_confidences["invoice_number"] = inv_conf
    if not inv_num:
        missing_fields.append("invoice_number")

    # 5. Purchase Order Number (Optional)
    po_num = None
    po_conf = 0.0
    po_patterns = [
        r"(?i)(?:purchase\s*order\s*(?:no|number|#|num)?|p\.?o\.?\s*(?:no|number|#|num)?[:.\s]+)\s*([A-Za-z0-9-_/]+)",
        r"(?i)\b(PO-[A-Za-z0-9-]+)\b",
    ]
    for pat in po_patterns:
        m = re.search(pat, raw_text)
        if m:
            cand = m.group(1).strip()
            if len(cand) > 2 and cand.upper() not in ["N/A", "NONE", "NIL", "NOT"]:
                po_num = cand
                po_conf = 0.90
                break

    po_id = None
    if po_num:
        po_rec = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.ilike(po_num)).first()
        if po_rec:
            po_id = po_rec.id
            po_conf = 0.98

    field_confidences["purchase_order"] = po_conf

    # 6. Dates: Invoice Date & Due Date
    inv_date = None
    inv_date_conf = 0.0
    date_patterns = [
        r"(?i)(?:invoice\s*date|date\s*of\s*issue|issue\s*date|dated)[:.\s]+([^\n\r]+)",
        r"(?i)\bdate[:.\s]+([^\n\r]+)",
    ]
    for pat in date_patterns:
        m = re.search(pat, raw_text)
        if m:
            parsed = parse_date_string(m.group(1))
            if parsed:
                inv_date = parsed
                inv_date_conf = 0.95
                break

    field_confidences["invoice_date"] = inv_date_conf
    if not inv_date:
        missing_fields.append("invoice_date")

    due_date = None
    due_date_conf = 0.0
    due_patterns = [
        r"(?i)(?:due\s*date|payment\s*due|pay\s*by)[:.\s]+([^\n\r]+)",
    ]
    for pat in due_patterns:
        m = re.search(pat, raw_text)
        if m:
            parsed = parse_date_string(m.group(1))
            if parsed:
                due_date = parsed
                due_date_conf = 0.90
                break

    field_confidences["due_date"] = due_date_conf

    # 7. Financial Extraction & Mathematical Reconciliation
    financials = extract_financial_fields(raw_text, lines)
    subtotal = financials["subtotal"]
    tax_amount = financials["tax_amount"]
    total_amount = financials["total_amount"]

    field_confidences["subtotal"] = 0.95 if subtotal is not None else 0.0
    field_confidences["tax_amount"] = 0.95 if tax_amount is not None else 0.0
    field_confidences["total_amount"] = 0.95 if total_amount is not None else 0.0

    if not total_amount:
        missing_fields.append("total_amount")
    if not subtotal:
        missing_fields.append("subtotal")

    # 8. Currency Detection
    currency = extract_currency(raw_text)
    field_confidences["currency"] = 0.95

    # 9. Description / Line Summary
    description = None
    desc_m = re.search(
        r"(?i)(?:description|items?|scope\s*of\s*work)[:.\s]+([^\n\r]+)",
        raw_text,
    )
    if desc_m:
        description = desc_m.group(1).strip()
    elif len(lines) > 2:
        for ln in lines[1:5]:
            if (
                len(ln) > 10
                and not re.search(r"(?i)(?:gstin|tel|address|original|tax|date)", ln)
                and ln != vendor_name
            ):
                description = ln
                break

    # 10. Comprehensive Extraction Confidence Score
    weights = {
        "vendor_name": 0.25,
        "invoice_number": 0.25,
        "total_amount": 0.20,
        "subtotal": 0.15,
        "invoice_date": 0.10,
        "tax_amount": 0.05,
    }
    base_conf = sum(field_confidences.get(k, 0.0) * w for k, w in weights.items()) * 100

    # Adjust confidence by financial reconciliation
    if financials["reconciliation_status"] == "RECONCILED":
        # Bonus for reconciled financial math
        base_conf = min(base_conf * 1.05, 98.0)
    elif financials["reconciliation_status"] == "DISCREPANCY":
        # Penalty for math discrepancy
        base_conf = min(base_conf * 0.70, 65.0)

    overall_score = round(Decimal(str(base_conf)), 2)

    return {
        "vendor_id": vendor_id,
        "vendor_code": vendor_code,
        "vendor_name": vendor_name,
        "customer_name": customer_name,
        "customer_gstin": customer_gstin,
        "invoice_number": inv_num,
        "purchase_order_id": po_id,
        "purchase_order_number": po_num,
        "invoice_date": inv_date,
        "due_date": due_date,
        "subtotal": subtotal or Decimal("0.00"),
        "cgst_amount": financials["cgst"],
        "sgst_amount": financials["sgst"],
        "igst_amount": financials["igst"],
        "tax_amount": tax_amount or Decimal("0.00"),
        "total_amount": total_amount or Decimal("0.00"),
        "discount_amount": financials["discount"],
        "roundoff_amount": financials["roundoff"],
        "currency": currency,
        "description": description,
        "tax_identifier": tax_id,
        "reconciliation_status": financials["reconciliation_status"],
        "reconciliation_message": financials["reconciliation_message"],
        "confidence_score": overall_score,
        "field_confidences": field_confidences,
        "missing_fields": missing_fields,
    }


def detect_duplicates(
    db: Session,
    file_hash: Optional[str],
    vendor_id: Optional[int],
    invoice_number: Optional[str],
    current_invoice_id: Optional[int] = None,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """Checks for duplicate invoice documents and duplicate vendor invoice numbers.

    Returns:
        (is_duplicate, duplicate_reason, existing_invoice_id)
    """
    # 1. Exact document file hash check
    if file_hash:
        query = db.query(Invoice).filter(Invoice.file_hash == file_hash)
        if current_invoice_id:
            query = query.filter(Invoice.id != current_invoice_id)
        existing_by_hash = query.first()
        if existing_by_hash:
            return (
                True,
                f"Identical document file has already been uploaded as Invoice #{existing_by_hash.invoice_number} (ID: {existing_by_hash.id}).",
                existing_by_hash.id,
            )

    # 2. Same vendor + normalized invoice number check
    if vendor_id and invoice_number:
        norm_num = normalize_invoice_number(invoice_number)
        query = db.query(Invoice).filter(
            Invoice.vendor_id == vendor_id,
            Invoice.normalized_invoice_number == norm_num,
        )
        if current_invoice_id:
            query = query.filter(Invoice.id != current_invoice_id)
        existing_by_vendor_num = query.first()
        if existing_by_vendor_num:
            return (
                True,
                f"Invoice number '{invoice_number}' already exists in records for Vendor ID {vendor_id} (Invoice ID: {existing_by_vendor_num.id}).",
                existing_by_vendor_num.id,
            )

    return False, None, None
