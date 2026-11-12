from datetime import date, datetime
from decimal import Decimal
import logging
import re
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session, joinedload

from app.models.budget import Budget
from app.models.department import Department
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.vendor import Vendor
from app.services.agents.approval_recommendation_agent import ApprovalRecommendationAgent
from app.services.agents.config_loader import (
    get_approval_policies,
    get_department_budget_rules,
    get_fraud_thresholds,
    get_matching_tolerances,
    get_tax_rules,
    get_vendor_verification_rules,
)
from app.services.agents.fraud_risk_agent import FraudRiskAgent
from app.services.agents.invoice_understanding_agent import InvoiceUnderstandingAgent
from app.services.agents.matching_agent import ThreeWayMatchingAgent
from app.services.agents.vendor_verification_agent import VendorVerificationAgent

logger = logging.getLogger("bahi_ai.agents.tools")


# --------------------------------------------------------------------------
# 1. Pydantic Argument Schemas (Input Validation)
# --------------------------------------------------------------------------
class InvoiceIdArg(BaseModel):
    invoice_id: int = Field(..., description="The internal database ID of the invoice to inspect.")


class VendorDetailsArg(BaseModel):
    vendor_id: int = Field(..., description="The database ID of the vendor to retrieve.")


class PurchaseOrderArg(BaseModel):
    po_identifier: str = Field(..., description="Purchase Order number (e.g. PO-2024-001) or PO ID.")


class DepartmentBudgetArg(BaseModel):
    department_id: int = Field(..., description="The database ID of the university department cost center.")


class ApprovalPolicyArg(BaseModel):
    amount: float = Field(..., ge=0, description="The gross invoice amount in INR to evaluate for approval delegation.")


class HumanReviewArg(BaseModel):
    invoice_id: int = Field(..., description="The internal database ID of the invoice.")
    reason: str = Field(..., min_length=5, description="Clear, concise justification why officer review is required.")
    recommended_action: str = Field(
        ...,
        description="Recommended action for the human officer: 'APPROVE', 'REVIEW', or 'REJECT'.",
    )
    key_evidence: List[str] = Field(default=[], description="Bullet points of verified facts supporting this recommendation.")


# --------------------------------------------------------------------------
# 2. Sanitization Helper (Redacts sensitive bank accounts, tokens, secrets)
# --------------------------------------------------------------------------
def sanitize_tool_output(obj: Any) -> Any:
    """Recursively converts Decimals/dates and redacts sensitive bank credentials."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ["password", "token", "secret", "api_key"]):
                clean[k] = "[REDACTED]"
            elif "bank_account" in k_lower and isinstance(v, str) and len(v) > 4:
                clean[k] = f"****{v[-4:]}"
            else:
                clean[k] = sanitize_tool_output(v)
        return clean
    if isinstance(obj, list):
        return [sanitize_tool_output(x) for x in obj]
    return obj


# --------------------------------------------------------------------------
# 3. Tool Implementations (Python executes, Gemini selects)
# --------------------------------------------------------------------------
class APToolRegistry:
    """Registry of safe, narrowly scoped backend tools for accounts payable orchestration.
    Every tool validates arguments with Pydantic and executes deterministic database/agent logic.
    Gemini cannot execute arbitrary code or queries.
    """

    def __init__(self):
        self.understanding_agent = InvoiceUnderstandingAgent()
        self.vendor_agent = VendorVerificationAgent()
        self.matching_agent = ThreeWayMatchingAgent()
        self.risk_agent = FraudRiskAgent()
        self.recommendation_agent = ApprovalRecommendationAgent()

    # Tool 1
    def get_invoice_details(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Retrieves verified invoice header, itemized lines, and OCR extraction metadata.
        Use this tool first to understand the invoice number, vendor ID, department ID, subtotal, and tax totals.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = (
            db.query(Invoice)
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.department),
                joinedload(Invoice.lines),
            )
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        lines = [
            {
                "line_number": line.line_number,
                "description": line.description,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price),
                "tax_rate": float(line.tax_rate),
                "line_total": float(line.line_total),
            }
            for line in (invoice.lines or [])
        ]

        gst_breakdown = (invoice.extraction_metadata or {}).get("gst_breakdown", {})

        return sanitize_tool_output({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "vendor_id": invoice.vendor_id,
            "vendor_name": invoice.vendor.legal_name if invoice.vendor else None,
            "purchase_order_id": invoice.purchase_order_id,
            "department_id": invoice.department_id,
            "department_code": invoice.department.code if invoice.department else None,
            "invoice_date": invoice.invoice_date,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "currency": invoice.currency,
            "ocr_confidence": invoice.confidence_score,
            "processing_status": invoice.processing_status,
            "approval_status": invoice.approval_status,
            "payment_status": invoice.payment_status,
            "line_items": lines,
            "gst_breakdown": gst_breakdown,
        })

    # Tool 2
    def get_vendor_details(self, db: Session, vendor_id: int) -> Dict[str, Any]:
        """Retrieves official vendor record from the university vendor master directory.
        Use this tool to check legal vendor name, code, registered GSTIN, bank details, and active status.
        """
        VendorDetailsArg(vendor_id=vendor_id)
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if not vendor:
            return {"error": f"Vendor with ID {vendor_id} not found in university vendor master."}

        return sanitize_tool_output({
            "id": vendor.id,
            "vendor_code": vendor.vendor_code,
            "legal_name": vendor.legal_name,
            "tax_identifier": vendor.tax_identifier,
            "is_active": vendor.is_active,
            "has_bank_details": bool(vendor.bank_account_number and vendor.bank_ifsc_code),
            "payment_terms": vendor.payment_terms,
            "rating": float(vendor.rating) if vendor.rating else None,
        })

    # Tool 3
    def verify_vendor_status(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Runs the Vendor Verification Agent comparing invoice supplier header vs vendor master.
        Verifies GSTIN match, vendor active status, and flags unregistered or blacklisted suppliers.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        res = self.vendor_agent.execute(invoice, db)
        return sanitize_tool_output(res.model_dump(mode="json"))

    # Tool 4
    def get_purchase_order(self, db: Session, po_identifier: str) -> Dict[str, Any]:
        """Retrieves authorized Purchase Order (PO) details and approved line item rates.
        Use this tool to verify contracted quantities, unit prices, and PO total amount.
        """
        PurchaseOrderArg(po_identifier=po_identifier)
        clean_id = po_identifier.strip()
        query = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.lines))
        if clean_id.isdigit():
            po = query.filter(PurchaseOrder.id == int(clean_id)).first()
        else:
            po = query.filter(PurchaseOrder.po_number.ilike(clean_id)).first()

        if not po:
            return {"error": f"Purchase Order '{po_identifier}' not found in procurement records."}

        lines = [
            {
                "line_number": line.line_number,
                "description": line.description,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price),
                "total_amount": float(line.total_amount),
            }
            for line in (po.lines or [])
        ]

        return sanitize_tool_output({
            "id": po.id,
            "po_number": po.po_number,
            "vendor_id": po.vendor_id,
            "department_id": po.department_id,
            "status": po.status,
            "total_amount": po.total_amount,
            "currency": po.currency,
            "lines": lines,
        })

    # Tool 5
    def get_grn_details(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Retrieves Goods Receipt Notes (GRN) linked to the invoice's purchase order.
        Use this tool to check physical receipt confirmation, accepted quantities, and inspection status.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice or not invoice.purchase_order_id:
            return {"error": "Invoice has no linked Purchase Order to look up Goods Receipts for."}

        grns = (
            db.query(GoodsReceipt)
            .options(joinedload(GoodsReceipt.lines))
            .filter(GoodsReceipt.purchase_order_id == invoice.purchase_order_id)
            .all()
        )
        if not grns:
            return {"has_grn": False, "message": "No Goods Receipt Notes registered for this Purchase Order."}

        results = []
        for grn in grns:
            results.append({
                "grn_number": grn.grn_number,
                "status": grn.status,
                "received_date": grn.received_date,
                "lines": [
                    {
                        "quantity_ordered": float(l.quantity_ordered),
                        "quantity_received": float(l.quantity_received),
                        "quantity_accepted": float(l.quantity_accepted),
                        "quantity_rejected": float(l.quantity_rejected),
                    }
                    for l in (grn.lines or [])
                ],
            })

        return sanitize_tool_output({"has_grn": True, "goods_receipts": results})

    # Tool 6
    def check_duplicate_invoice(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Checks for duplicate invoice submissions using SHA-256 hash and normalized invoice number.
        Use this tool to verify whether this invoice was already uploaded or previously paid.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        # Check duplicate file hash
        hash_dupes = []
        if invoice.file_hash:
            hash_dupes = (
                db.query(Invoice)
                .filter(Invoice.file_hash == invoice.file_hash, Invoice.id != invoice.id)
                .all()
            )

        # Check vendor + normalized number collision
        number_dupes = []
        if invoice.vendor_id and invoice.normalized_invoice_number:
            number_dupes = (
                db.query(Invoice)
                .filter(
                    Invoice.vendor_id == invoice.vendor_id,
                    Invoice.normalized_invoice_number == invoice.normalized_invoice_number,
                    Invoice.id != invoice.id,
                )
                .all()
            )

        is_duplicate = len(hash_dupes) > 0 or len(number_dupes) > 0
        details = []
        if hash_dupes:
            details.append(f"Identical file content (SHA-256) matches existing Invoice ID #{hash_dupes[0].id}")
        if number_dupes:
            details.append(f"Same supplier and invoice number collision with existing Invoice ID #{number_dupes[0].id}")

        return sanitize_tool_output({
            "is_duplicate": is_duplicate,
            "hash_matches_count": len(hash_dupes),
            "number_matches_count": len(number_dupes),
            "details": details,
        })

    # Tool 7
    def validate_invoice_totals(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Checks mathematical reconciliation: Subtotal + Tax == Total.
        Use this tool to detect clerical mistakes, rounding issues, or unstated charges.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        sub = invoice.subtotal or Decimal("0.00")
        tax = invoice.tax_amount or Decimal("0.00")
        tot = invoice.total_amount or Decimal("0.00")

        expected_total = sub + tax
        diff = abs(expected_total - tot)
        is_reconciled = diff <= Decimal("0.05") or (diff <= Decimal("1.00"))

        return sanitize_tool_output({
            "subtotal": sub,
            "tax_amount": tax,
            "total_amount": tot,
            "expected_total": expected_total,
            "difference": diff,
            "is_reconciled": is_reconciled,
            "status": "RECONCILED" if is_reconciled else "DISCREPANCY",
        })

    # Tool 8
    def check_department_budget(self, db: Session, department_id: int) -> Dict[str, Any]:
        """Checks university department cost center budget allocation, spent amount, and available balance.
        Use this tool to verify whether the faculty has sufficient remaining funds for this invoice.
        """
        DepartmentBudgetArg(department_id=department_id)
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            return {"error": f"Department with ID {department_id} not found."}

        budget = db.query(Budget).filter(Budget.department_id == department_id).order_by(Budget.id.desc()).first()
        if not budget:
            return {
                "department_code": dept.code,
                "department_name": dept.name,
                "has_budget": False,
                "message": "No active fiscal year budget allocated to this department.",
            }

        util_pct = (
            float(budget.spent_amount) / float(budget.allocated_amount) * 100.0
            if budget.allocated_amount and float(budget.allocated_amount) > 0
            else 0.0
        )

        return sanitize_tool_output({
            "department_code": dept.code,
            "department_name": dept.name,
            "fiscal_year": budget.fiscal_year,
            "allocated_amount": budget.allocated_amount,
            "committed_amount": budget.committed_amount,
            "spent_amount": budget.spent_amount,
            "available_amount": budget.available_amount,
            "utilization_percentage": round(util_pct, 2),
            "is_near_limit": util_pct >= 80.0,
            "is_exhausted": float(budget.available_amount) <= 0.0,
        })

    # Tool 9
    def run_three_way_matching(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Executes the Three-Way Matching Agent comparing invoice line items vs PO rates vs GRN quantities.
        Use this tool to check for overbilling, price variances, or missing deliveries.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        res = self.matching_agent.execute(invoice, db)
        return sanitize_tool_output(res.model_dump(mode="json"))

    # Tool 10
    def run_fraud_analysis(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Executes the Fraud & Risk Detection Agent computing a risk score (0-100) across 7 dimensions.
        Use this tool to detect anomaly signals, overbilling flags, and vendor verification risks.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        understanding = self.understanding_agent.execute(invoice)
        vendor = self.vendor_agent.execute(invoice, db)
        matching = self.matching_agent.execute(invoice, db)
        risk = self.risk_agent.execute(invoice, db, understanding, vendor, matching)
        return sanitize_tool_output(risk.model_dump(mode="json"))

    # Tool 11
    def run_invoice_understanding(self, db: Session, invoice_id: int) -> Dict[str, Any]:
        """Executes the Invoice Understanding Agent assessing OCR quality, missing fields, and tax type.
        Use this tool to inspect extraction confidence, line item clarity, and regional tax structures.
        """
        InvoiceIdArg(invoice_id=invoice_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": f"Invoice with ID {invoice_id} not found."}

        understanding = self.understanding_agent.execute(invoice)
        return sanitize_tool_output(understanding.model_dump(mode="json"))

    # Tool 12
    def get_applicable_approval_policy(self, db: Session, amount: float) -> Dict[str, Any]:
        """Evaluates university financial policies to determine the required approval authority tier.
        Use this tool to find out which officer (HOD, Finance Officer, or Finance Administrator) must sign off.
        """
        ApprovalPolicyArg(amount=amount)
        policies = get_approval_policies()
        matched_tier = None
        for tier in policies.tiers:
            if tier.max_amount is None or amount <= tier.max_amount:
                matched_tier = tier
                break

        if not matched_tier and policies.tiers:
            matched_tier = policies.tiers[-1]

        return sanitize_tool_output({
            "amount": amount,
            "required_role": matched_tier.role if matched_tier else "FINANCE_ADMIN",
            "tier_number": matched_tier.tier if matched_tier else 3,
            "tier_title": matched_tier.title if matched_tier else "Finance Administrator",
            "scope": matched_tier.scope if matched_tier else "General university procurement",
        })

    # Tool 13
    def request_human_review(
        self,
        db: Session,
        invoice_id: int,
        reason: str,
        recommended_action: str,
        key_evidence: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Concludes AI orchestration and requests formal human officer review.
        Use this tool when sufficient evidence has been collected to formulate a final recommendation.
        """
        validated = HumanReviewArg(
            invoice_id=invoice_id,
            reason=reason,
            recommended_action=recommended_action.upper(),
            key_evidence=key_evidence or [],
        )

        return sanitize_tool_output({
            "status": "HUMAN_REVIEW_SCHEDULED",
            "invoice_id": validated.invoice_id,
            "recommended_action": validated.recommended_action,
            "reason": validated.reason,
            "key_evidence": validated.key_evidence,
            "message": "Human review task scheduled. Agents do not execute approvals or payments autonomously.",
        })

    def get_tool_names(self) -> List[str]:
        return [
            "get_invoice_details",
            "get_vendor_details",
            "verify_vendor_status",
            "get_purchase_order",
            "get_grn_details",
            "check_duplicate_invoice",
            "validate_invoice_totals",
            "check_department_budget",
            "run_three_way_matching",
            "run_fraud_analysis",
            "run_invoice_understanding",
            "get_applicable_approval_policy",
            "request_human_review",
        ]

    def execute_tool(self, name: str, args: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Dispatches a tool call with strict Pydantic argument validation and sandboxed execution."""
        try:
            if name == "get_invoice_details":
                validated = InvoiceIdArg(**args)
                return self.get_invoice_details(db, validated.invoice_id)
            elif name == "get_vendor_details":
                validated = VendorDetailsArg(**args)
                return self.get_vendor_details(db, validated.vendor_id)
            elif name == "verify_vendor_status":
                validated = InvoiceIdArg(**args)
                return self.verify_vendor_status(db, validated.invoice_id)
            elif name == "get_purchase_order":
                validated = PurchaseOrderArg(**args)
                return self.get_purchase_order(db, validated.po_identifier)
            elif name == "get_grn_details":
                validated = InvoiceIdArg(**args)
                return self.get_grn_details(db, validated.invoice_id)
            elif name == "check_duplicate_invoice":
                validated = InvoiceIdArg(**args)
                return self.check_duplicate_invoice(db, validated.invoice_id)
            elif name == "validate_invoice_totals":
                validated = InvoiceIdArg(**args)
                return self.validate_invoice_totals(db, validated.invoice_id)
            elif name == "check_department_budget":
                validated = DepartmentBudgetArg(**args)
                return self.check_department_budget(db, validated.department_id)
            elif name == "run_three_way_matching":
                validated = InvoiceIdArg(**args)
                return self.run_three_way_matching(db, validated.invoice_id)
            elif name == "run_fraud_analysis":
                validated = InvoiceIdArg(**args)
                return self.run_fraud_analysis(db, validated.invoice_id)
            elif name == "run_invoice_understanding":
                validated = InvoiceIdArg(**args)
                return self.run_invoice_understanding(db, validated.invoice_id)
            elif name == "get_applicable_approval_policy":
                validated = ApprovalPolicyArg(**args)
                return self.get_applicable_approval_policy(db, validated.amount)
            elif name == "request_human_review":
                validated = HumanReviewArg(**args)
                return self.request_human_review(
                    db=db,
                    invoice_id=validated.invoice_id,
                    reason=validated.reason,
                    recommended_action=validated.recommended_action,
                    key_evidence=validated.key_evidence,
                )
            else:
                return {"error": f"Unknown tool '{name}'. Valid tools are: {self.get_tool_names()}"}
        except ValidationError as ve:
            return {"error": f"Invalid arguments for tool '{name}': {ve.errors()}"}
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}


# Global tool registry instance
tool_registry = APToolRegistry()


# --------------------------------------------------------------------------
# 4. Declarative Tool Callables for Google GenAI Function Calling
# --------------------------------------------------------------------------
def get_invoice_details(invoice_id: int) -> dict:
    """Retrieves verified invoice header, itemized lines, and OCR extraction metadata.

    Args:
        invoice_id: The internal database ID of the invoice to inspect.
    """
    return {}


def get_vendor_details(vendor_id: int) -> dict:
    """Retrieves official vendor record from the university vendor master directory.

    Args:
        vendor_id: The database ID of the vendor to retrieve.
    """
    return {}


def verify_vendor_status(invoice_id: int) -> dict:
    """Runs the Vendor Verification Agent comparing invoice supplier header vs vendor master.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def get_purchase_order(po_identifier: str) -> dict:
    """Retrieves authorized Purchase Order (PO) details and approved line item rates.

    Args:
        po_identifier: Purchase Order number (e.g. PO-2024-001) or PO ID.
    """
    return {}


def get_grn_details(invoice_id: int) -> dict:
    """Retrieves Goods Receipt Notes (GRN) linked to the invoice's purchase order.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def check_duplicate_invoice(invoice_id: int) -> dict:
    """Checks for duplicate invoice submissions using SHA-256 hash and normalized invoice number.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def validate_invoice_totals(invoice_id: int) -> dict:
    """Checks mathematical reconciliation: Subtotal + Tax == Total.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def check_department_budget(department_id: int) -> dict:
    """Checks university department cost center budget allocation, spent amount, and available balance.

    Args:
        department_id: The database ID of the university department cost center.
    """
    return {}


def run_three_way_matching(invoice_id: int) -> dict:
    """Executes the Three-Way Matching Agent comparing invoice line items vs PO rates vs GRN quantities.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def run_fraud_analysis(invoice_id: int) -> dict:
    """Executes the Fraud & Risk Detection Agent computing a risk score (0-100) across 7 dimensions.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def run_invoice_understanding(invoice_id: int) -> dict:
    """Executes the Invoice Understanding Agent assessing OCR quality, missing fields, and tax type.

    Args:
        invoice_id: The internal database ID of the invoice.
    """
    return {}


def get_applicable_approval_policy(amount: float) -> dict:
    """Evaluates university financial policies to determine the required approval authority tier.

    Args:
        amount: The gross invoice amount in INR to evaluate.
    """
    return {}


def request_human_review(
    invoice_id: int,
    reason: str,
    recommended_action: str,
    key_evidence: Optional[List[str]] = None,
) -> dict:
    """Concludes AI orchestration and requests formal human officer review with verified findings.

    Args:
        invoice_id: The internal database ID of the invoice.
        reason: Clear, concise justification why officer review is required.
        recommended_action: Recommended action for the human officer: 'APPROVE', 'REVIEW', or 'REJECT'.
        key_evidence: Bullet points of verified facts supporting this recommendation.
    """
    return {}


def get_orchestration_tools() -> List[Callable]:
    """Returns the list of 13 function callables for Google GenAI function calling."""
    return [
        get_invoice_details,
        get_vendor_details,
        verify_vendor_status,
        get_purchase_order,
        get_grn_details,
        check_duplicate_invoice,
        validate_invoice_totals,
        check_department_budget,
        run_three_way_matching,
        run_fraud_analysis,
        run_invoice_understanding,
        get_applicable_approval_policy,
        request_human_review,
    ]
