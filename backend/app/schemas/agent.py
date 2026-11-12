from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentExecutionLogResponse(BaseModel):
    id: int
    invoice_id: Optional[int] = None
    agent_name: str
    execution_status: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_message: Optional[str] = None
    execution_duration: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceUnderstandingResult(BaseModel):
    agent_name: str = "InvoiceUnderstandingAgent"
    status: str  # "PASSED" | "WARNING" | "FAILED"
    confidence_score: Decimal
    tax_type: str
    math_reconciled: bool
    discrepancy_amount: Decimal = Decimal("0.00")
    missing_fields: List[str] = []
    abnormalities: List[str] = []
    summary: str
    details: Dict[str, Any] = {}


class VendorVerificationResult(BaseModel):
    agent_name: str = "VendorVerificationAgent"
    status: str  # "VERIFIED" | "UNKNOWN_VENDOR" | "GSTIN_MISMATCH" | "INACTIVE_VENDOR" | "NAME_MISMATCH"
    vendor_id: Optional[int] = None
    vendor_code: Optional[str] = None
    legal_name: Optional[str] = None
    invoice_vendor_name: Optional[str] = None
    invoice_gstin: Optional[str] = None
    registered_gstin: Optional[str] = None
    gstin_matched: bool = False
    is_active: bool = False
    has_bank_details: bool = False
    summary: str
    reasons: List[str] = []


class LineItemMatch(BaseModel):
    line_number: int
    description: str
    po_quantity: Optional[Decimal] = None
    grn_accepted_quantity: Optional[Decimal] = None
    invoice_quantity: Decimal
    po_unit_price: Optional[Decimal] = None
    invoice_unit_price: Decimal
    price_variance: Decimal = Decimal("0.00")
    quantity_variance: Decimal = Decimal("0.00")
    status: str  # "MATCHED" | "PRICE_VARIANCE" | "QUANTITY_VARIANCE" | "UNMATCHED"


class ThreeWayMatchingResult(BaseModel):
    agent_name: str = "ThreeWayMatchingAgent"
    match_status: str  # "FULL_MATCH" | "PARTIAL_MATCH" | "PRICE_VARIANCE" | "QUANTITY_VARIANCE" | "NO_PO" | "NO_GRN" | "DISCREPANCY"
    po_number: Optional[str] = None
    po_total: Optional[Decimal] = None
    invoice_total: Optional[Decimal] = None
    total_variance: Decimal = Decimal("0.00")
    grn_numbers: List[str] = []
    line_matches: List[LineItemMatch] = []
    discrepancies: List[str] = []
    summary: str


class RiskFactor(BaseModel):
    factor: str
    score_impact: int
    severity: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    description: str


class FraudRiskResult(BaseModel):
    agent_name: str = "FraudRiskAgent"
    risk_score: Decimal = Field(..., ge=0, le=100)
    risk_category: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    risk_factors: List[RiskFactor] = []
    recommended_action: str
    summary: str


class ApprovalRecommendationResult(BaseModel):
    agent_name: str = "ApprovalRecommendationAgent"
    recommendation: str  # "APPROVE" | "REVIEW" | "REJECT"
    confidence: Decimal
    executive_summary: str
    key_reasons: List[str] = []
    unresolved_issues: List[str] = []
    action_checklist: List[str] = []


class MultiAgentAnalysisReport(BaseModel):
    invoice_id: int
    orchestrator_status: str  # "COMPLETED" | "FAILED" | "PARTIAL"
    recommendation: str  # "APPROVE" | "REVIEW" | "REJECT"
    risk_score: Decimal
    risk_category: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    understanding: InvoiceUnderstandingResult
    vendor_verification: VendorVerificationResult
    matching: ThreeWayMatchingResult
    fraud_risk: FraudRiskResult
    approval_recommendation: ApprovalRecommendationResult
    execution_logs: List[AgentExecutionLogResponse] = []
    unresolved_issues: List[str] = []
    analyzed_at: datetime
