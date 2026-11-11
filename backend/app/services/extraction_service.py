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


def clean_amount(val_str: str) -> Optional[Decimal]:
    """Safely converts currency string to Decimal without floating-point math."""
    if not val_str:
        return None
    # Remove currency symbols and whitespace
    clean = re.sub(r"[^\d.,]", "", val_str).strip()
    if not clean:
        return None

    # Handle European style (1.234,56) vs US style (1,234.56)
    if "," in clean and "." in clean:
        if clean.rfind(",") > clean.rfind("."):
            # European format: 1.234,56 -> 1234.56
            clean = clean.replace(".", "").replace(",", ".")
        else:
            # US format: 1,234.56 -> 1234.56
            clean = clean.replace(",", "")
    elif "," in clean:
        # Could be 1234,56 or 1,234
        parts = clean.split(",")
        if len(parts[-1]) == 2:
            clean = clean.replace(",", ".")
        else:
            clean = clean.replace(",", "")

    try:
        dec = Decimal(clean)
        return dec.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_date_string(date_str: str) -> Optional[date]:
    """Attempts to parse common date formats into a date object."""
    if not date_str:
        return None

    clean = re.sub(r"[^\w\s/.-]", "", date_str).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.date()
        except ValueError:
            continue

    # Regex search for ISO format YYYY-MM-DD
    iso_match = re.search(r"\b(20\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01]))\b", clean)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(1).replace("/", "-"), "%Y-%m-%d").date()
        except ValueError:
            pass

    return None


def extract_currency(text: str) -> str:
    """Detects currency symbol or code from document text."""
    if "USD" in text or "$" in text:
        return "USD"
    if "EUR" in text or "€" in text:
        return "EUR"
    if "GBP" in text or "£" in text:
        return "GBP"
    if "INR" in text or "₹" in text or "Rs" in text:
        return "INR"
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

        # Check legal name
        for v in vendors:
            v_name = v.legal_name.lower().strip()
            if v_name in normalized_text:
                return v, 0.95
            # Substring match for principal name (e.g. "Apex Computing" from "Apex Computing Solutions Inc.")
            words = [w for w in v_name.split() if len(w) > 3 and w not in ["inc", "llc", "corp", "ltd", "solutions", "services", "company"]]
            if len(words) >= 2 and " ".join(words[:2]) in normalized_text:
                return v, 0.85

        # Check tax identifier if present
        for v in vendors:
            if v.tax_identifier and v.tax_identifier.lower() in normalized_text:
                return v, 0.99

        return None, 0.0
    except Exception as e:
        logger.warning(f"Error matching vendor against database: {e}")
        return None, 0.0


def extract_fields_from_text(raw_text: str, db: Session) -> Dict[str, Any]:
    """Performs heuristic and regex parsing on raw document text to extract
    the 11 specified invoice fields and calculate field-level confidences.
    """
    field_confidences: Dict[str, float] = {}
    missing_fields: List[str] = []

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    # 1. Vendor Extraction & Matching
    matched_vendor, vendor_conf = match_registered_vendor(raw_text, db)
    vendor_name = matched_vendor.legal_name if matched_vendor else None
    vendor_id = matched_vendor.id if matched_vendor else None
    vendor_code = matched_vendor.vendor_code if matched_vendor else None

    if not vendor_name:
        # Fallback heuristic: look for top header line or "Vendor:" / "From:"
        v_match = re.search(r"(?i)(?:vendor|seller|supplier|from)[:.\s]+([^\n\r,]+)", raw_text)
        if v_match:
            vendor_name = v_match.group(1).strip()
            vendor_conf = 0.60
        elif len(lines) > 0:
            vendor_name = lines[0]
            vendor_conf = 0.40
        else:
            vendor_name = None
            vendor_conf = 0.0

    field_confidences["vendor_name"] = vendor_conf
    if not vendor_name or vendor_conf < 0.5:
        missing_fields.append("vendor")

    # 2. Invoice Number
    inv_num = None
    inv_conf = 0.0
    inv_patterns = [
        r"(?i)\b(?:invoice\s*(?:no|number|#|num|id)[:.\s]*)\s*([A-Za-z0-9-_/]{3,30})\b",
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
        # Try generic ID pattern
        m = re.search(r"\b([A-Z]{2,4}-[0-9]{4}-[0-9]{3,6})\b", raw_text)
        if m:
            inv_num = m.group(1).strip()
            inv_conf = 0.70

    field_confidences["invoice_number"] = inv_conf
    if not inv_num:
        missing_fields.append("invoice_number")

    # 3. Purchase Order Number
    po_num = None
    po_conf = 0.0
    po_patterns = [
        r"(?i)(?:purchase\s*order\s*(?:no|number|#|num)?|p\.?o\.?\s*(?:no|number|#|num)?[:.\s]+)\s*([A-Za-z0-9-_/]+)",
        r"(?i)\b(PO-[A-Za-z0-9-]+)\b",
    ]
    for pat in po_patterns:
        m = re.search(pat, raw_text)
        if m:
            po_num = m.group(1).strip()
            po_conf = 0.90
            break

    # Look up PO in database to verify existence
    po_id = None
    if po_num:
        po_rec = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.ilike(po_num)).first()
        if po_rec:
            po_id = po_rec.id
            po_conf = 0.98

    field_confidences["purchase_order"] = po_conf

    # 4. Dates: Invoice Date & Due Date
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
                inv_date_conf = 0.90
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
    if not due_date:
        missing_fields.append("due_date")

    # 5. Financials: Total, Subtotal, Tax
    total_amount = None
    total_conf = 0.0
    total_patterns = [
        r"(?i)\btotal(?:\s+(?:amount|due|payable|balance|net))*[:.\s]*[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
        r"(?i)(?:grand\s*total|net\s*payable|balance\s*due|amount\s*due)[:.\s]*[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
        r"(?i)\btotal[:.\s]*[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)\b",
    ]
    for pat in total_patterns:
        m = re.search(pat, raw_text)
        if m:
            dec = clean_amount(m.group(1))
            if dec and dec > 0:
                total_amount = dec
                total_conf = 0.95
                break

    field_confidences["total_amount"] = total_conf
    if not total_amount:
        missing_fields.append("total_amount")

    subtotal = None
    subtotal_conf = 0.0
    subtotal_patterns = [
        r"(?i)(?:sub\s*total|subtotal|net\s*amount)[:.\s]*[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
    ]
    for pat in subtotal_patterns:
        m = re.search(pat, raw_text)
        if m:
            dec = clean_amount(m.group(1))
            if dec and dec >= 0:
                subtotal = dec
                subtotal_conf = 0.90
                break

    field_confidences["subtotal"] = subtotal_conf

    tax_amount = None
    tax_conf = 0.0
    tax_patterns = [
        r"(?i)(?:tax(?:\s*\([^)]+\))?|vat|gst|sales\s*tax|tax\s*amount)[:.\s]*[$€£₹]?\s*([0-9,]+(?:\.[0-9]{2})?)",
    ]
    for pat in tax_patterns:
        m = re.search(pat, raw_text)
        if m:
            dec = clean_amount(m.group(1))
            if dec and dec >= 0:
                tax_amount = dec
                tax_conf = 0.85
                break

    field_confidences["tax_amount"] = tax_conf

    # Reconcile subtotal and tax if one is missing but total is present
    if total_amount and subtotal and not tax_amount:
        if total_amount >= subtotal:
            tax_amount = total_amount - subtotal
            field_confidences["tax_amount"] = 0.75
    elif total_amount and not subtotal and not tax_amount:
        subtotal = total_amount
        tax_amount = Decimal("0.00")
        field_confidences["subtotal"] = 0.70
        field_confidences["tax_amount"] = 0.70

    # 6. Currency
    currency = extract_currency(raw_text)
    field_confidences["currency"] = 0.90

    # 7. Tax Identification Number
    tax_id = None
    tax_id_conf = 0.0
    tax_id_patterns = [
        r"(?i)(?:tax\s*(?:id|identifier|no)|ein|gstin|tin)[:.\s]+([A-Za-z0-9-]+)",
    ]
    for pat in tax_id_patterns:
        m = re.search(pat, raw_text)
        if m:
            tax_id = m.group(1).strip()
            tax_id_conf = 0.90
            break

    field_confidences["tax_identifier"] = tax_id_conf

    # 8. Description / Summary
    description = None
    desc_m = re.search(r"(?i)(?:description|items?|scope\s*of\s*work)[:.\s]+([^\n\r]+)", raw_text)
    if desc_m:
        description = desc_m.group(1).strip()
    elif len(lines) > 2:
        description = lines[1] if len(lines[1]) > 10 else lines[2]

    # Calculate overall extraction confidence (weighted average)
    weights = {
        "vendor_name": 0.25,
        "invoice_number": 0.25,
        "total_amount": 0.25,
        "invoice_date": 0.15,
        "due_date": 0.10,
    }
    overall_conf = sum(field_confidences.get(k, 0.0) * w for k, w in weights.items()) * 100
    overall_score = round(Decimal(str(overall_conf)), 2)

    return {
        "vendor_id": vendor_id,
        "vendor_code": vendor_code,
        "vendor_name": vendor_name,
        "invoice_number": inv_num,
        "purchase_order_id": po_id,
        "purchase_order_number": po_num,
        "invoice_date": inv_date,
        "due_date": due_date,
        "subtotal": subtotal or Decimal("0.00"),
        "tax_amount": tax_amount or Decimal("0.00"),
        "total_amount": total_amount or Decimal("0.00"),
        "currency": currency,
        "description": description,
        "tax_identifier": tax_id,
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
