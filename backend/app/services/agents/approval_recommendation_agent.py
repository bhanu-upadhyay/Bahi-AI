from decimal import Decimal
import logging
from typing import List, Optional
from app.models.invoice import Invoice
from app.schemas.agent import (
    ApprovalRecommendationResult,
    FraudRiskResult,
    InvoiceUnderstandingResult,
    ThreeWayMatchingResult,
    VendorVerificationResult,
)

logger = logging.getLogger("bahi_ai.agents.approval_recommendation")


class ApprovalRecommendationAgent:
    """Agent 5 — Approval Recommendation Agent
    Synthesizes findings from Invoice Understanding, Vendor Verification,
    Three-Way Matching, and Fraud/Risk Detection to recommend an intelligent
    action (APPROVE, REVIEW, or REJECT) for authorized human finance staff.
    Does NOT automatically alter approval or payment status.
    """

    def __init__(self, name: str = "ApprovalRecommendationAgent"):
        self.name = name

    def execute(
        self,
        invoice: Invoice,
        understanding_res: InvoiceUnderstandingResult,
        vendor_res: VendorVerificationResult,
        matching_res: ThreeWayMatchingResult,
        risk_res: FraudRiskResult,
    ) -> ApprovalRecommendationResult:
        logger.info(f"[{self.name}] Generating approval recommendation for Invoice #{invoice.invoice_number}")

        key_reasons: List[str] = []
        unresolved_issues: List[str] = []
        action_checklist: List[str] = []

        # 1. Evaluate Critical Reject Conditions
        is_reject = False
        if risk_res.risk_category == "CRITICAL":
            is_reject = True
            key_reasons.append(f"Critical risk level ({risk_res.risk_score}/100) flagged by Risk Engine.")
            critical_found = False
            for rf in risk_res.risk_factors:
                if rf.severity in ["CRITICAL", "HIGH"]:
                    unresolved_issues.append(f"CRITICAL: {rf.description}")
                    critical_found = True
            if not critical_found:
                unresolved_issues.append(f"Critical fraud/policy risk score of {risk_res.risk_score}/100.")

        if vendor_res.status == "INACTIVE_VENDOR":
            is_reject = True
            key_reasons.append("Vendor is inactive in university vendor master.")
            unresolved_issues.append("Vendor account is disabled. Invoices from inactive vendors cannot be settled.")

        if is_reject:
            recommendation = "REJECT"
            confidence = Decimal("0.95")
            executive_summary = (
                f"Recommendation: REJECT Invoice #{invoice.invoice_number}. "
                "Significant policy or fraud risks detected that prevent standard processing. "
                "Staff must formally reject or hold this submission."
            )
            action_checklist = [
                "Notify department procurement officer of rejection",
                "Log exception in university audit trail",
                "Flag vendor account for compliance inspection if duplicate submission suspected",
            ]
            return ApprovalRecommendationResult(
                recommendation=recommendation,
                confidence=confidence,
                executive_summary=executive_summary,
                key_reasons=key_reasons,
                unresolved_issues=unresolved_issues,
                action_checklist=action_checklist,
            )

        # 2. Evaluate Review vs Approve Conditions
        is_review = False

        # Vendor verification factors
        if vendor_res.status == "UNKNOWN_VENDOR":
            is_review = True
            key_reasons.append("Supplier is not yet registered in university vendor master.")
            unresolved_issues.append("Vendor onboarding required: collect W-9/PAN, GSTIN certificate, and bank details.")
            action_checklist.append("Submit new vendor registration request to Procurement")
        elif vendor_res.status == "GSTIN_MISMATCH":
            is_review = True
            key_reasons.append("Tax identifier mismatch between invoice and vendor master.")
            unresolved_issues.append(f"GSTIN conflict: {vendor_res.invoice_gstin} on invoice vs {vendor_res.registered_gstin} on master record.")
            action_checklist.append("Obtain updated GSTIN registration certificate from supplier")
        elif not vendor_res.has_bank_details:
            unresolved_issues.append("Vendor master record lacks verified bank remittance details.")
            action_checklist.append("Request banking mandate form before payment scheduling")

        # Three-way matching factors
        if matching_res.match_status == "QUANTITY_VARIANCE":
            is_review = True
            key_reasons.append("Invoiced quantity exceeds warehouse accepted goods receipt quantity.")
            for disc in matching_res.discrepancies:
                unresolved_issues.append(disc)
            action_checklist.append("Verify with Receiving / Warehouse team whether additional items arrived")
        elif matching_res.match_status == "PRICE_VARIANCE":
            is_review = True
            key_reasons.append("Invoiced unit price exceeds authorized Purchase Order rate.")
            for disc in matching_res.discrepancies:
                unresolved_issues.append(disc)
            action_checklist.append("Seek HOD authorization for unit price variance")
        elif matching_res.match_status == "NO_GRN":
            is_review = True
            key_reasons.append("No Goods Receipt Notes (GRN) confirmed for linked Purchase Order.")
            unresolved_issues.append("Goods delivery pending receipt in university warehouse.")
            action_checklist.append("Confirm delivery completion with lab/department manager")
        elif matching_res.match_status == "NO_PO":
            is_review = True
            key_reasons.append("Direct spend without Purchase Order reference.")
            unresolved_issues.append("Non-PO spend requires manual departmental budget verification.")
            action_checklist.append("Confirm HOD signature for direct departmental expenditure")

        # Understanding & Math factors
        if not understanding_res.math_reconciled:
            is_review = True
            key_reasons.append("Financial mathematics reconciliation failed.")
            for abn in understanding_res.abnormalities:
                unresolved_issues.append(abn)
            action_checklist.append("Review line items to determine correct payable amount")

        if understanding_res.status == "WARNING":
            for abn in understanding_res.abnormalities:
                if abn not in unresolved_issues:
                    unresolved_issues.append(abn)

        # Risk score factors
        if risk_res.risk_category in ["MEDIUM", "HIGH"]:
            is_review = True
            key_reasons.append(f"Risk Engine computed {risk_res.risk_category} risk ({risk_res.risk_score}/100).")
            for rf in risk_res.risk_factors:
                if rf.severity in ["HIGH", "MEDIUM"] and rf.description not in unresolved_issues:
                    unresolved_issues.append(rf.description)

        # 3. Decision Finalization
        if is_review:
            recommendation = "REVIEW"
            confidence = Decimal("0.88")
            executive_summary = (
                f"Recommendation: REVIEW Invoice #{invoice.invoice_number}. "
                "Automated checks identified items requiring human verification before payment can be authorized. "
                "Review the checklist below."
            )
            if not action_checklist:
                action_checklist.append("Verify invoice data against departmental records")
        else:
            recommendation = "APPROVE"
            confidence = Decimal("0.96")
            executive_summary = (
                f"Recommendation: APPROVE Invoice #{invoice.invoice_number}. "
                "Three-way match clean, vendor identity verified, financial math accurate, and risk score low. "
                "Ready for human approver sign-off."
            )
            key_reasons.append("Supplier identity verified against vendor master with matching GSTIN.")
            key_reasons.append("Three-way match confirmed against authorized PO and accepted GRN.")
            key_reasons.append("Financial mathematics reconciled perfectly with zero discrepancies.")
            key_reasons.append("Fraud risk score is LOW (clean history).")
            action_checklist = [
                "Conduct final visual review of invoice document",
                "Approve invoice in Bahi-AI approval workflow",
                "Schedule payment according to vendor credit terms",
            ]

        return ApprovalRecommendationResult(
            recommendation=recommendation,
            confidence=confidence,
            executive_summary=executive_summary,
            key_reasons=key_reasons,
            unresolved_issues=unresolved_issues,
            action_checklist=action_checklist,
        )
