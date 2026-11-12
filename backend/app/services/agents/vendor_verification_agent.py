import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.schemas.agent import VendorVerificationResult

logger = logging.getLogger("bahi_ai.agents.vendor_verification")


class VendorVerificationAgent:
    """Agent 2 — Vendor Verification Agent
    Verifies supplier identity against the university Vendor Master directory.
    Validates legal registration, active status, tax identifier (GSTIN/EIN) match,
    and banking readiness without altering vendor records.
    """

    def __init__(self, name: str = "VendorVerificationAgent"):
        self.name = name

    def execute(self, invoice: Invoice, db: Session) -> VendorVerificationResult:
        logger.info(f"[{self.name}] Verifying vendor for Invoice #{invoice.invoice_number}")

        reasons: List[str] = []
        vendor: Optional[Vendor] = None

        # 1. Look up vendor
        if invoice.vendor_id:
            vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()

        # If not linked by vendor_id, attempt lookup by tax_identifier or legal_name in DB
        if not vendor and invoice.tax_identifier:
            clean_id = invoice.tax_identifier.strip().upper()
            vendor = db.query(Vendor).filter(Vendor.tax_identifier.ilike(clean_id)).first()

        gst_meta = (invoice.extraction_metadata or {}).get("gst_breakdown") or {}
        extracted_supp_name = gst_meta.get("supplier_name")

        if not vendor and extracted_supp_name:
            clean_supp = extracted_supp_name.strip()
            vendor = db.query(Vendor).filter(Vendor.legal_name.ilike(f"%{clean_supp}%")).first()

        # 2. Case: Unknown / Unregistered Vendor
        if not vendor:
            supp_label = extracted_supp_name or invoice.tax_identifier or "Unknown Supplier"
            reasons.append(
                f"Vendor '{supp_label}' is not found in the university approved vendor master directory. "
                "Supplier onboarding and verification required prior to payment authorization."
            )
            return VendorVerificationResult(
                status="UNKNOWN_VENDOR",
                vendor_id=None,
                vendor_code=None,
                legal_name=None,
                invoice_vendor_name=extracted_supp_name,
                invoice_gstin=invoice.tax_identifier,
                registered_gstin=None,
                gstin_matched=False,
                is_active=False,
                has_bank_details=False,
                summary=f"Supplier '{supp_label}' is unverified and not registered in the vendor master.",
                reasons=reasons,
            )

        # 3. Case: Inactive Vendor
        if not vendor.is_active:
            reasons.append(
                f"Vendor '{vendor.legal_name}' ({vendor.vendor_code}) is marked INACTIVE in vendor master. "
                "Transactions and payments are blocked for inactive accounts."
            )
            return VendorVerificationResult(
                status="INACTIVE_VENDOR",
                vendor_id=vendor.id,
                vendor_code=vendor.vendor_code,
                legal_name=vendor.legal_name,
                invoice_vendor_name=extracted_supp_name,
                invoice_gstin=invoice.tax_identifier,
                registered_gstin=vendor.tax_identifier,
                gstin_matched=False,
                is_active=False,
                has_bank_details=bool(vendor.bank_account_last_four),
                summary=f"Vendor '{vendor.legal_name}' is inactive. Invoices cannot be processed.",
                reasons=reasons,
            )

        # 4. GSTIN / Tax ID Verification
        gstin_matched = False
        inv_gstin = (invoice.tax_identifier or "").strip().upper()
        reg_gstin = (vendor.tax_identifier or "").strip().upper()

        if inv_gstin and reg_gstin:
            if inv_gstin == reg_gstin:
                gstin_matched = True
            else:
                reasons.append(
                    f"GSTIN / Tax ID mismatch: Invoice documents '{inv_gstin}', but vendor master registers '{reg_gstin}'."
                )
                return VendorVerificationResult(
                    status="GSTIN_MISMATCH",
                    vendor_id=vendor.id,
                    vendor_code=vendor.vendor_code,
                    legal_name=vendor.legal_name,
                    invoice_vendor_name=extracted_supp_name,
                    invoice_gstin=inv_gstin,
                    registered_gstin=reg_gstin,
                    gstin_matched=False,
                    is_active=vendor.is_active,
                    has_bank_details=bool(vendor.bank_account_last_four),
                    summary=f"Vendor '{vendor.legal_name}' flagged with tax identifier conflict ({inv_gstin} vs {reg_gstin}).",
                    reasons=reasons,
                )
        elif not inv_gstin and reg_gstin:
            reasons.append(f"Invoice does not display GSTIN / Tax ID, whereas vendor master records '{reg_gstin}'.")
        elif inv_gstin and not reg_gstin:
            reasons.append(f"Vendor master lacks tax registration; invoice displays '{inv_gstin}'.")

        # 5. Vendor Legal Name Consistency Check
        name_matched = True
        if extracted_supp_name:
            v_name_clean = re.sub(r"[^\w\s]", "", vendor.legal_name.lower())
            inv_name_clean = re.sub(r"[^\w\s]", "", extracted_supp_name.lower())
            # Substring or overlap check
            words_v = set(w for w in v_name_clean.split() if len(w) > 3)
            words_inv = set(w for w in inv_name_clean.split() if len(w) > 3)
            if words_v and words_inv and not (words_v & words_inv):
                name_matched = False
                reasons.append(
                    f"Document header name '{extracted_supp_name}' differs substantially from registered name '{vendor.legal_name}'."
                )

        # 6. Bank Details Check
        has_bank = bool(vendor.bank_account_last_four and vendor.bank_name)
        if not has_bank:
            reasons.append(
                f"Vendor '{vendor.legal_name}' has incomplete bank account details on file. Remittance setup required."
            )

        status = "NAME_MISMATCH" if not name_matched else "VERIFIED"
        summary = (
            f"Vendor '{vendor.legal_name}' ({vendor.vendor_code}) is approved and active in vendor master."
            + (f" GSTIN '{reg_gstin}' verified." if gstin_matched else "")
            + (" Banking details on file." if has_bank else " (Pending bank details update).")
        )

        return VendorVerificationResult(
            status=status,
            vendor_id=vendor.id,
            vendor_code=vendor.vendor_code,
            legal_name=vendor.legal_name,
            invoice_vendor_name=extracted_supp_name,
            invoice_gstin=inv_gstin or None,
            registered_gstin=reg_gstin or None,
            gstin_matched=gstin_matched,
            is_active=vendor.is_active,
            has_bank_details=has_bank,
            summary=summary,
            reasons=reasons,
        )
