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
from app.services.agents.fraud_risk_agent import FraudRiskAgent
from app.services.agents.invoice_understanding_agent import InvoiceUnderstandingAgent
from app.services.agents.matching_agent import ThreeWayMatchingAgent
from app.services.agents.vendor_verification_agent import VendorVerificationAgent

logger = logging.getLogger("bahi_ai.agents.orchestrator")


class AgentOrchestrator:
    """Central orchestration service coordinating the 5 specialized AI agents
    for accounts payable automation:
      1. InvoiceUnderstandingAgent
      2. VendorVerificationAgent
      3. ThreeWayMatchingAgent
      4. FraudRiskAgent
      5. ApprovalRecommendationAgent
    Ensures traceable execution logs, idempotency, graceful error handling,
    and strict separation between agent recommendations and human decision authority.
    """

    def __init__(self):
        self.understanding_agent = InvoiceUnderstandingAgent()
        self.vendor_agent = VendorVerificationAgent()
        self.matching_agent = ThreeWayMatchingAgent()
        self.risk_agent = FraudRiskAgent()
        self.recommendation_agent = ApprovalRecommendationAgent()

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
        """Orchestrates the multi-agent analysis pipeline for the given invoice."""
        start_overall = time.time()
        logger.info(f"[AgentOrchestrator] Starting multi-agent analysis for Invoice ID {invoice_id}")

        invoice = (
            db.query(Invoice)
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.department),
                joinedload(Invoice.purchase_order),
                joinedload(Invoice.lines),
                joinedload(Invoice.fraud_alerts),
            )
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found.")

        orchestrator_status = "COMPLETED"
        execution_logs: list[AgentExecutionLogResponse] = []

        # -------------------------------------------------------------
        # 1. Invoice Understanding Agent
        # -------------------------------------------------------------
        t0 = time.time()
        try:
            understanding_res = self.understanding_agent.execute(invoice)
            d0 = Decimal(str(round(time.time() - t0, 4)))
            log0 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.understanding_agent.name,
                status="COMPLETED",
                input_summary=f"Analyzed OCR fields for Invoice #{invoice.invoice_number}",
                output_summary=understanding_res.summary,
                duration=d0,
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log0))
        except Exception as e:
            logger.error(f"Error in {self.understanding_agent.name}: {e}", exc_info=True)
            d0 = Decimal(str(round(time.time() - t0, 4)))
            log0 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.understanding_agent.name,
                status="FAILED",
                input_summary=f"Failed parsing Invoice #{invoice.invoice_number}",
                output_summary="Agent execution threw exception",
                duration=d0,
                error_message=str(e),
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log0))
            raise RuntimeError(f"Agent {self.understanding_agent.name} failed: {e}")

        # -------------------------------------------------------------
        # 2. Vendor Verification Agent
        # -------------------------------------------------------------
        t1 = time.time()
        try:
            vendor_res = self.vendor_agent.execute(invoice, db)
            d1 = Decimal(str(round(time.time() - t1, 4)))
            log1 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.vendor_agent.name,
                status="COMPLETED",
                input_summary=f"Verified vendor ID {invoice.vendor_id} / Tax ID {invoice.tax_identifier}",
                output_summary=vendor_res.summary,
                duration=d1,
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log1))
        except Exception as e:
            logger.error(f"Error in {self.vendor_agent.name}: {e}", exc_info=True)
            d1 = Decimal(str(round(time.time() - t1, 4)))
            log1 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.vendor_agent.name,
                status="FAILED",
                input_summary="Vendor verification lookup failed",
                output_summary="Agent execution threw exception",
                duration=d1,
                error_message=str(e),
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log1))
            raise RuntimeError(f"Agent {self.vendor_agent.name} failed: {e}")

        # -------------------------------------------------------------
        # 3. Three-Way Matching Agent
        # -------------------------------------------------------------
        t2 = time.time()
        try:
            matching_res = self.matching_agent.execute(invoice, db)
            d2 = Decimal(str(round(time.time() - t2, 4)))
            log2 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.matching_agent.name,
                status="COMPLETED",
                input_summary=f"Cross-verified against PO #{matching_res.po_number or 'None'}",
                output_summary=matching_res.summary,
                duration=d2,
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log2))
        except Exception as e:
            logger.error(f"Error in {self.matching_agent.name}: {e}", exc_info=True)
            d2 = Decimal(str(round(time.time() - t2, 4)))
            log2 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.matching_agent.name,
                status="FAILED",
                input_summary="Three-way matching execution failed",
                output_summary="Agent execution threw exception",
                duration=d2,
                error_message=str(e),
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log2))
            raise RuntimeError(f"Agent {self.matching_agent.name} failed: {e}")

        # -------------------------------------------------------------
        # 4. Fraud & Risk Detection Agent
        # -------------------------------------------------------------
        t3 = time.time()
        try:
            risk_res = self.risk_agent.execute(
                invoice=invoice,
                db=db,
                understanding_res=understanding_res,
                vendor_res=vendor_res,
                matching_res=matching_res,
            )
            d3 = Decimal(str(round(time.time() - t3, 4)))
            log3 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.risk_agent.name,
                status="COMPLETED",
                input_summary=f"Synthesized risk across 7 dimensions for Invoice #{invoice.invoice_number}",
                output_summary=risk_res.summary,
                duration=d3,
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log3))
        except Exception as e:
            logger.error(f"Error in {self.risk_agent.name}: {e}", exc_info=True)
            d3 = Decimal(str(round(time.time() - t3, 4)))
            log3 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.risk_agent.name,
                status="FAILED",
                input_summary="Risk assessment failed",
                output_summary="Agent execution threw exception",
                duration=d3,
                error_message=str(e),
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log3))
            raise RuntimeError(f"Agent {self.risk_agent.name} failed: {e}")

        # -------------------------------------------------------------
        # 5. Approval Recommendation Agent
        # -------------------------------------------------------------
        t4 = time.time()
        try:
            rec_res = self.recommendation_agent.execute(
                invoice=invoice,
                understanding_res=understanding_res,
                vendor_res=vendor_res,
                matching_res=matching_res,
                risk_res=risk_res,
            )
            d4 = Decimal(str(round(time.time() - t4, 4)))
            log4 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.recommendation_agent.name,
                status="COMPLETED",
                input_summary="Synthesized findings of all 4 prior agents",
                output_summary=rec_res.executive_summary,
                duration=d4,
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log4))
        except Exception as e:
            logger.error(f"Error in {self.recommendation_agent.name}: {e}", exc_info=True)
            d4 = Decimal(str(round(time.time() - t4, 4)))
            log4 = self._log_agent_execution(
                db=db,
                invoice_id=invoice.id,
                agent_name=self.recommendation_agent.name,
                status="FAILED",
                input_summary="Recommendation synthesis failed",
                output_summary="Agent execution threw exception",
                duration=d4,
                error_message=str(e),
            )
            execution_logs.append(AgentExecutionLogResponse.model_validate(log4))
            raise RuntimeError(f"Agent {self.recommendation_agent.name} failed: {e}")

        # -------------------------------------------------------------
        # 6. Update Processing Status & Metadata
        # -------------------------------------------------------------
        # Update processing_status based on match & risk without overwriting approval/payment status
        if rec_res.recommendation == "APPROVE" and matching_res.match_status == "FULL_MATCH":
            invoice.processing_status = "MATCHED"
        elif rec_res.recommendation in ["REVIEW", "REJECT"] or risk_res.risk_category in ["HIGH", "CRITICAL"]:
            invoice.processing_status = "EXCEPTION"

        now_utc = datetime.now(timezone.utc)
        report = MultiAgentAnalysisReport(
            invoice_id=invoice.id,
            orchestrator_status=orchestrator_status,
            recommendation=rec_res.recommendation,
            risk_score=risk_res.risk_score,
            risk_category=risk_res.risk_category,
            understanding=understanding_res,
            vendor_verification=vendor_res,
            matching=matching_res,
            fraud_risk=risk_res,
            approval_recommendation=rec_res,
            execution_logs=execution_logs,
            unresolved_issues=rec_res.unresolved_issues,
            analyzed_at=now_utc,
        )

        # Persist consolidated report into invoice.extraction_metadata
        meta = dict(invoice.extraction_metadata or {})
        meta["agent_analysis"] = report.model_dump(mode="json")
        invoice.extraction_metadata = meta

        # Record audit log event
        audit = AuditLog(
            action="MULTI_AGENT_ANALYSIS_COMPLETED",
            entity_type="INVOICE",
            entity_id=str(invoice.id),
            new_values={
                "recommendation": rec_res.recommendation,
                "risk_score": float(risk_res.risk_score),
                "risk_category": risk_res.risk_category,
                "match_status": matching_res.match_status,
                "vendor_status": vendor_res.status,
                "duration_seconds": round(time.time() - start_overall, 3),
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(invoice)

        logger.info(
            f"[AgentOrchestrator] Completed analysis for Invoice #{invoice.invoice_number}: "
            f"Recommendation={rec_res.recommendation}, Risk={risk_res.risk_score} ({risk_res.risk_category})"
        )
        return report

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
