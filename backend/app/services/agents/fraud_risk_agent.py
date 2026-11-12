from decimal import Decimal
import logging
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, normalize_invoice_number
from app.models.payment import Payment
from app.schemas.agent import (
    FraudRiskResult,
    InvoiceUnderstandingResult,
    RiskFactor,
    ThreeWayMatchingResult,
    VendorVerificationResult,
)

logger = logging.getLogger("bahi_ai.agents.fraud_risk")


class FraudRiskAgent:
    """Agent 4 — Fraud & Risk Detection Agent
    Evaluates multi-dimensional risk signals across document duplication,
    vendor identity fidelity, tax consistency, duplicate disbursement risks,
    and purchase order deviations.
    Calculates an explainable 0–100 risk score and categorizes risk into LOW, MEDIUM, HIGH, CRITICAL.
    """

    def __init__(self, name: str = "FraudRiskAgent"):
        self.name = name

    def execute(
        self,
        invoice: Invoice,
        db: Session,
        understanding_res: Optional[InvoiceUnderstandingResult] = None,
        vendor_res: Optional[VendorVerificationResult] = None,
        matching_res: Optional[ThreeWayMatchingResult] = None,
    ) -> FraudRiskResult:
        logger.info(f"[{self.name}] Assessing fraud and risk for Invoice #{invoice.invoice_number}")

        risk_score = 0
        risk_factors: List[RiskFactor] = []

        # 1. Duplicate Document & File Hash Check
        if invoice.file_hash:
            dup_hash = (
                db.query(Invoice)
                .filter(Invoice.file_hash == invoice.file_hash, Invoice.id != invoice.id)
                .first()
            )
            if dup_hash:
                risk_score += 85
                risk_factors.append(
                    RiskFactor(
                        factor="EXACT_DOCUMENT_DUPLICATE",
                        score_impact=85,
                        severity="CRITICAL",
                        description=f"Identical document file hash already exists on record as Invoice #{dup_hash.invoice_number} (ID: {dup_hash.id}).",
                    )
                )

        # 2. Logical Duplicate (Same Vendor + Normalized Invoice Number)
        if invoice.vendor_id and invoice.invoice_number:
            norm_num = normalize_invoice_number(invoice.invoice_number)
            # Remove any -DUP- suffix when checking
            clean_norm = norm_num.split("-DUP-")[0]
            dup_logical = (
                db.query(Invoice)
                .filter(
                    Invoice.vendor_id == invoice.vendor_id,
                    Invoice.normalized_invoice_number.ilike(f"{clean_norm}%"),
                    Invoice.id != invoice.id,
                )
                .first()
            )
            if dup_logical and not any(rf.factor == "EXACT_DOCUMENT_DUPLICATE" for rf in risk_factors):
                risk_score += 75
                risk_factors.append(
                    RiskFactor(
                        factor="DUPLICATE_INVOICE_NUMBER",
                        score_impact=75,
                        severity="CRITICAL",
                        description=f"Vendor ID {invoice.vendor_id} already has settled or recorded invoice with number '{invoice.invoice_number}' (ID: {dup_logical.id}).",
                    )
                )

        # 3. Duplicate Payment Risk
        if invoice.vendor_id and invoice.total_amount:
            past_payment = (
                db.query(Payment)
                .join(Invoice, Payment.invoice_id == Invoice.id)
                .filter(
                    Invoice.vendor_id == invoice.vendor_id,
                    Payment.amount == invoice.total_amount,
                    Payment.status.in_(["PAID", "SCHEDULED"]),
                    Invoice.id != invoice.id,
                )
                .first()
            )
            if past_payment:
                risk_score += 30
                risk_factors.append(
                    RiskFactor(
                        factor="POTENTIAL_DUPLICATE_PAYMENT",
                        score_impact=30,
                        severity="HIGH",
                        description=f"Payment #{past_payment.payment_reference} for identical amount ({invoice.currency} {invoice.total_amount}) to this vendor is already recorded.",
                    )
                )

        # 4. Vendor Identity Risk Signals
        if vendor_res:
            if vendor_res.status == "UNKNOWN_VENDOR":
                risk_score += 25
                risk_factors.append(
                    RiskFactor(
                        factor="UNKNOWN_VENDOR",
                        score_impact=25,
                        severity="MEDIUM",
                        description=f"Supplier is not registered in the university approved vendor master directory.",
                    )
                )
            elif vendor_res.status == "INACTIVE_VENDOR":
                risk_score += 45
                risk_factors.append(
                    RiskFactor(
                        factor="INACTIVE_VENDOR",
                        score_impact=45,
                        severity="HIGH",
                        description=f"Vendor account is inactive or suspended in system records.",
                    )
                )
            elif vendor_res.status == "GSTIN_MISMATCH":
                risk_score += 35
                risk_factors.append(
                    RiskFactor(
                        factor="TAX_IDENTIFIER_MISMATCH",
                        score_impact=35,
                        severity="HIGH",
                        description=f"Tax identifier on invoice ({vendor_res.invoice_gstin}) conflicts with registered GSTIN ({vendor_res.registered_gstin}).",
                    )
                )

            if not vendor_res.has_bank_details and vendor_res.status == "VERIFIED":
                risk_score += 10
                risk_factors.append(
                    RiskFactor(
                        factor="MISSING_BANK_REMITTANCE",
                        score_impact=10,
                        severity="LOW",
                        description="Vendor master lacks verified bank remittance details for electronic transfer.",
                    )
                )

        # 5. Three-Way Matching Risk Signals
        if matching_res:
            if matching_res.match_status == "QUANTITY_VARIANCE":
                risk_score += 40
                risk_factors.append(
                    RiskFactor(
                        factor="QUANTITY_OVERBILLING",
                        score_impact=40,
                        severity="HIGH",
                        description="Invoiced quantity exceeds confirmed goods receipt quantities accepted by warehouse.",
                    )
                )
            elif matching_res.match_status == "PRICE_VARIANCE":
                risk_score += 30
                risk_factors.append(
                    RiskFactor(
                        factor="PRICE_VARIANCE",
                        score_impact=30,
                        severity="MEDIUM",
                        description=f"Invoiced price exceeds authorized unit rate on PO #{matching_res.po_number}.",
                    )
                )
            elif matching_res.match_status == "NO_GRN":
                risk_score += 20
                risk_factors.append(
                    RiskFactor(
                        factor="MISSING_GOODS_RECEIPT",
                        score_impact=20,
                        severity="MEDIUM",
                        description="Purchase Order exists but no warehouse Goods Receipt Note (GRN) confirms delivery.",
                    )
                )
            elif matching_res.match_status == "NO_PO":
                # Direct spend
                if invoice.total_amount and invoice.total_amount > Decimal("5000.00"):
                    risk_score += 15
                    risk_factors.append(
                        RiskFactor(
                            factor="HIGH_VALUE_DIRECT_SPEND",
                            score_impact=15,
                            severity="LOW",
                            description="High-value direct expenditure submitted without an associated Purchase Order.",
                        )
                    )

        # 6. Invoice Understanding & Math Signals
        if understanding_res:
            if not understanding_res.math_reconciled:
                risk_score += 30
                risk_factors.append(
                    RiskFactor(
                        factor="FINANCIAL_INCONSISTENCY",
                        score_impact=30,
                        severity="HIGH",
                        description=f"Mathematical discrepancy: Subtotal + Tax does not match Invoiced Grand Total (Variance: {understanding_res.discrepancy_amount}).",
                    )
                )
            if understanding_res.confidence_score < Decimal("70.00"):
                risk_score += 15
                risk_factors.append(
                    RiskFactor(
                        factor="LOW_EXTRACTION_CONFIDENCE",
                        score_impact=15,
                        severity="LOW",
                        description=f"OCR character/field extraction confidence ({understanding_res.confidence_score}%) is low, increasing risk of clerical error.",
                    )
                )

        # 7. Pattern Anomalies
        inv_num = invoice.invoice_number or ""
        if inv_num in ["1234", "0001", "TEST", "SAMPLE", "9999"]:
            risk_score += 20
            risk_factors.append(
                RiskFactor(
                    factor="SUSPICIOUS_INVOICE_NUMBER",
                    score_impact=20,
                    severity="MEDIUM",
                    description=f"Invoice number '{inv_num}' follows an unusual generic or placeholder sequence.",
                )
            )

        # Final score bounding
        final_risk = min(risk_score, 100)

        # Determine Category
        if final_risk >= 85:
            risk_category = "CRITICAL"
            recommended_action = "Reject or freeze invoice immediately; escalate to Internal Audit and Senior Finance Administrator."
        elif final_risk >= 60:
            risk_category = "HIGH"
            recommended_action = "Hold processing; require departmental re-confirmation and vendor tax compliance review."
        elif final_risk >= 30:
            risk_category = "MEDIUM"
            recommended_action = "Route to Procurement Officer and HOD for manual exception verification."
        else:
            risk_category = "LOW"
            recommended_action = "Proceed with standard three-way approval pipeline."

        # Summary
        if final_risk >= 60:
            summary = (
                f"Elevated risk flagged ({final_risk}/100, {risk_category}). "
                f"Key factors: {'; '.join(rf.description for rf in risk_factors[:2])}. "
                f"Action: {recommended_action}"
            )
        elif final_risk >= 30:
            summary = (
                f"Moderate risk signals detected ({final_risk}/100, {risk_category}). "
                f"Review required for: {'; '.join(rf.description for rf in risk_factors[:2])}."
            )
        else:
            summary = (
                f"Low risk assessment ({final_risk}/100, {risk_category}). "
                "Document attributes, tax mathematics, and vendor relationship appear consistent with standard AP policies."
            )

        return FraudRiskResult(
            risk_score=Decimal(str(final_risk)),
            risk_category=risk_category,
            risk_factors=risk_factors,
            recommended_action=recommended_action,
            summary=summary,
        )
