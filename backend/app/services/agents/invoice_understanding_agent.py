from datetime import date, timedelta
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
from app.models.invoice import Invoice
from app.schemas.agent import InvoiceUnderstandingResult

logger = logging.getLogger("bahi_ai.agents.invoice_understanding")


class InvoiceUnderstandingAgent:
    """Agent 1 — Invoice Understanding Agent
    Analyzes OCR-extracted invoice information, validates data completeness,
    assesses extraction confidence, verifies tax calculations and regional tax structures,
    and identifies mathematical discrepancies or missing mandatory fields.
    """

    def __init__(self, name: str = "InvoiceUnderstandingAgent"):
        self.name = name

    def execute(self, invoice: Invoice) -> InvoiceUnderstandingResult:
        logger.info(f"[{self.name}] Analyzing Invoice #{invoice.invoice_number} (ID: {invoice.id})")

        missing_fields: List[str] = []
        abnormalities: List[str] = []

        # 1. Inspect Mandatory Fields
        if not invoice.invoice_number or invoice.invoice_number.startswith("PENDING-"):
            missing_fields.append("invoice_number")
            abnormalities.append("Invoice number is missing or auto-generated placeholder.")

        if not invoice.invoice_date:
            missing_fields.append("invoice_date")
            abnormalities.append("Invoice date is missing.")

        subtotal = invoice.subtotal if invoice.subtotal is not None else Decimal("0.00")
        tax_amount = invoice.tax_amount if invoice.tax_amount is not None else Decimal("0.00")
        total_amount = invoice.total_amount if invoice.total_amount is not None else Decimal("0.00")

        if total_amount <= Decimal("0.00"):
            missing_fields.append("total_amount")
            abnormalities.append("Total amount is zero or missing.")

        if subtotal <= Decimal("0.00"):
            missing_fields.append("subtotal")
            abnormalities.append("Subtotal (taxable amount) is zero or missing.")

        # 2. Date Sanity Verification
        today = date.today()
        inv_date = invoice.invoice_date
        if isinstance(inv_date, str):
            try:
                inv_date = date.fromisoformat(inv_date)
            except Exception:
                inv_date = None

        due_date = invoice.due_date
        if isinstance(due_date, str):
            try:
                due_date = date.fromisoformat(due_date)
            except Exception:
                due_date = None

        if inv_date:
            if inv_date > today + timedelta(days=30):
                abnormalities.append(
                    f"Invoice date {inv_date} is abnormally in the future (today: {today})."
                )

        if inv_date and due_date:
            if due_date < inv_date:
                abnormalities.append(
                    f"Due date ({due_date}) precedes invoice date ({inv_date})."
                )

        # 3. Tax Structure Identification & GST Validation
        gst_breakdown = (invoice.extraction_metadata or {}).get("gst_breakdown") or {}
        cgst = Decimal(str(gst_breakdown.get("cgst_amount") or "0.00")) if gst_breakdown.get("cgst_amount") else None
        sgst = Decimal(str(gst_breakdown.get("sgst_amount") or "0.00")) if gst_breakdown.get("sgst_amount") else None
        igst = Decimal(str(gst_breakdown.get("igst_amount") or "0.00")) if gst_breakdown.get("igst_amount") else None
        disc = Decimal(str(gst_breakdown.get("discount_amount") or "0.00")) if gst_breakdown.get("discount_amount") else Decimal("0.00")
        rnd = Decimal(str(gst_breakdown.get("roundoff_amount") or "0.00")) if gst_breakdown.get("roundoff_amount") else Decimal("0.00")

        # Double Taxation Guard: IGST and (CGST/SGST) are mutually exclusive under Indian GST
        has_double_taxation = False
        if igst and (cgst or sgst):
            has_double_taxation = True
            tax_type = "CONFLICT_DOUBLE_TAXATION (IGST + CGST/SGST)"
            abnormalities.append(
                f"Double taxation violation: Invoice charges both Inter-state IGST ({igst}) and Intra-state CGST/SGST (CGST: {cgst}, SGST: {sgst})."
            )
        elif cgst and sgst:
            tax_type = "INTRA_STATE_GST (CGST + SGST)"
            # Symmetry check: CGST and SGST must have equal amounts under statutory rules
            if abs(cgst - sgst) > Decimal("0.05"):
                abnormalities.append(
                    f"Asymmetric Intra-state GST: CGST ({cgst}) does not equal SGST ({sgst})."
                )
        elif igst:
            tax_type = "INTER_STATE_GST (IGST)"
        elif tax_amount > Decimal("0.00"):
            tax_type = "STANDARD_TAX / VAT"
        else:
            tax_type = "ZERO_RATED / EXEMPT"

        # Check if individual GST components sum up to total tax amount
        if (cgst or sgst or igst) and not has_double_taxation:
            tax_components_sum = (cgst or Decimal("0.00")) + (sgst or Decimal("0.00")) + (igst or Decimal("0.00"))
            if abs(tax_components_sum - tax_amount) > Decimal("0.50"):
                abnormalities.append(
                    f"Tax breakdown sum ({tax_components_sum}) does not match total invoice tax ({tax_amount})."
                )

        # 4. Mathematical Reconciliation Check
        expected_total = subtotal + tax_amount - disc + rnd
        discrepancy = abs(expected_total - total_amount)
        math_reconciled = (
            not has_double_taxation
            and (discrepancy <= Decimal("0.05") or (rnd != Decimal("0.00") and discrepancy <= Decimal("1.00")))
        )

        if not math_reconciled and not has_double_taxation:
            abnormalities.append(
                f"Financial reconciliation failed: Subtotal ({subtotal}) + Tax ({tax_amount})"
                + (f" - Discount ({disc})" if disc > 0 else "")
                + (f" + Rounding ({rnd})" if rnd != 0 else "")
                + f" = {expected_total}, but Grand Total is {total_amount} (Diff: {discrepancy})."
            )

        # 5. Line-Item Aggregation & Duplicate Line Detection (if lines present)
        invoice_lines = invoice.lines or []
        if invoice_lines:
            lines_subtotal = Decimal("0.00")
            seen_lines = set()
            for l in invoice_lines:
                l_qty = Decimal(str(l.quantity if l.quantity is not None else 0))
                l_price = Decimal(str(l.unit_price if l.unit_price is not None else 0))
                lines_subtotal += (l_qty * l_price).quantize(Decimal("0.01"))

                # Duplicate line signature
                line_sig = (l.description.strip().lower() if l.description else "", l_qty, l_price)
                if line_sig in seen_lines:
                    abnormalities.append(
                        f"Potential duplicate invoice line item: '{l.description}' (Qty: {l_qty}, Price: {l_price})."
                    )
                else:
                    seen_lines.add(line_sig)

            # Check if sum of line items aligns with invoice subtotal
            if subtotal > Decimal("0.00") and abs(lines_subtotal - subtotal) > Decimal("1.00"):
                abnormalities.append(
                    f"Line items subtotal sum ({lines_subtotal:,.2f}) does not match invoice subtotal ({subtotal:,.2f})."
                )

        # 6. Extraction Confidence Score Check
        conf_score = invoice.confidence_score if invoice.confidence_score is not None else Decimal("50.00")
        if conf_score < Decimal("70.00"):
            abnormalities.append(f"OCR extraction confidence ({conf_score}%) is below 70% threshold.")

        # 7. Overall Status Determination
        if len(missing_fields) > 0 or not math_reconciled or has_double_taxation or conf_score < Decimal("60.00"):
            status = "FAILED" if (len(missing_fields) > 1 or total_amount <= Decimal("0.00") or has_double_taxation) else "WARNING"
        elif len(abnormalities) > 0:
            status = "WARNING"
        else:
            status = "PASSED"

        # Formulate executive summary
        if status == "PASSED":
            summary = (
                f"Invoice #{invoice.invoice_number} successfully understood. Verified {tax_type} structure; "
                f"taxable subtotal {invoice.currency} {subtotal:,.2f} + tax {invoice.currency} {tax_amount:,.2f} "
                f"reconciles perfectly to grand total {invoice.currency} {total_amount:,.2f} ({conf_score:.1f}% confidence)."
            )
        elif status == "WARNING":
            summary = (
                f"Invoice #{invoice.invoice_number} understood with warnings: {'; '.join(abnormalities)} "
                f"({conf_score:.1f}% confidence)."
            )
        else:
            summary = (
                f"Invoice understanding flagged critical issues: Missing fields: {', '.join(missing_fields)}. "
                f"Abnormalities: {'; '.join(abnormalities)}."
            )

        details = {
            "currency": invoice.currency,
            "subtotal": str(subtotal),
            "tax_amount": str(tax_amount),
            "total_amount": str(total_amount),
            "discount_amount": str(disc),
            "roundoff_amount": str(rnd),
            "cgst_amount": str(cgst) if cgst is not None else None,
            "sgst_amount": str(sgst) if sgst is not None else None,
            "igst_amount": str(igst) if igst is not None else None,
            "ocr_method": invoice.ocr_method,
            "supplier_name_extracted": gst_breakdown.get("supplier_name"),
            "customer_name_extracted": gst_breakdown.get("customer_name"),
        }

        return InvoiceUnderstandingResult(
            status=status,
            confidence_score=conf_score,
            tax_type=tax_type,
            math_reconciled=math_reconciled,
            discrepancy_amount=discrepancy,
            missing_fields=missing_fields,
            abnormalities=abnormalities,
            summary=summary,
            details=details,
        )
