from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import time
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models.agent_execution_log import AgentExecutionLog
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.schemas.agent import (
    AgentExecutionLogResponse,
    MultiAgentAnalysisReport,
)
from app.services.agents.approval_recommendation_agent import ApprovalRecommendationAgent
from app.services.agents.dynamic_orchestrator import DynamicAPOrchestrator
from app.services.agents.fraud_risk_agent import FraudRiskAgent
from app.services.agents.invoice_understanding_agent import InvoiceUnderstandingAgent
from app.services.agents.matching_agent import ThreeWayMatchingAgent
from app.services.agents.vendor_verification_agent import VendorVerificationAgent

logger = logging.getLogger("bahi_ai.agents.orchestrator")


class AgentOrchestrator:
    """Central orchestration service coordinating accounts payable AI agents.
    Dispatches to DynamicAPOrchestrator (powered by Google Gemini) when configured,
    with seamless automatic fallback to the deterministic 5-agent pipeline.
    """

    def __init__(self, dynamic_orchestrator: Optional[DynamicAPOrchestrator] = None):
        self.understanding_agent = InvoiceUnderstandingAgent()
        self.vendor_agent = VendorVerificationAgent()
        self.matching_agent = ThreeWayMatchingAgent()
        self.risk_agent = FraudRiskAgent()
        self.recommendation_agent = ApprovalRecommendationAgent()
        self.dynamic_orchestrator = dynamic_orchestrator or DynamicAPOrchestrator()

    def _log_agent_execution(
        self,
        db: Session,
        invoice_id: int,
        agent_name: str,
        status: str,
        input_summary: str,
        output_summary: str,
        duration: Decimal,
        error_message: Optional[str] = None,
    ) -> AgentExecutionLog:
        """Appends an execution log record to agent_execution_logs table."""
        log = AgentExecutionLog(
            invoice_id=invoice_id,
            agent_name=agent_name,
            execution_status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            error_message=error_message,
            execution_duration=duration,
        )
        db.add(log)
        db.flush()
        return log

    def analyze_invoice(
        self,
        invoice_id: int,
        db: Session,
        force_reanalyze: bool = True,
    ) -> MultiAgentAnalysisReport:
        """Orchestrates multi-agent analysis for the invoice using dynamic Gemini orchestration
        with automatic fallback to rule-based pipeline."""
        return self.dynamic_orchestrator.analyze_invoice(
            invoice_id=invoice_id,
            db=db,
            force_reanalyze=force_reanalyze,
        )

    def get_latest_analysis(self, invoice_id: int, db: Session) -> Optional[MultiAgentAnalysisReport]:
        """Retrieves the latest cached multi-agent analysis report for an invoice."""
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return None

        meta = invoice.extraction_metadata or {}
        agent_data = meta.get("agent_analysis")
        if not agent_data:
            return None

        # Also load recent execution logs from DB for live traceability
        logs = (
            db.query(AgentExecutionLog)
            .filter(AgentExecutionLog.invoice_id == invoice_id)
            .order_by(AgentExecutionLog.created_at.desc())
            .limit(10)
            .all()
        )
        agent_data["execution_logs"] = [
            AgentExecutionLogResponse.model_validate(l).model_dump(mode="json") for l in reversed(logs)
        ]
        return MultiAgentAnalysisReport.model_validate(agent_data)
