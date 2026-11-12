from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.agent_execution_log import AgentExecutionLog
from app.models.invoice import Invoice
from app.schemas.agent import (
    AgentExecutionLogResponse,
    MultiAgentAnalysisReport,
)
from app.services.agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/agents", tags=["AI Agents & Orchestration"])
orchestrator = AgentOrchestrator()


@router.post("/analyze/{invoice_id}", response_model=MultiAgentAnalysisReport, status_code=status.HTTP_200_OK)
def run_agent_analysis(invoice_id: int, db: Session = Depends(get_db)):
    """Triggers the complete 5-agent AI intelligence pipeline for an invoice:
    1. InvoiceUnderstandingAgent
    2. VendorVerificationAgent
    3. ThreeWayMatchingAgent
    4. FraudRiskAgent
    5. ApprovalRecommendationAgent
    Saves traceable execution logs and returns the consolidated intelligence report.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found.",
        )

    try:
        report = orchestrator.analyze_invoice(invoice_id=invoice_id, db=db, force_reanalyze=True)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent orchestration error: {str(e)}",
        )


@router.get("/analysis/{invoice_id}", response_model=MultiAgentAnalysisReport)
def get_invoice_analysis(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieves the latest multi-agent analysis report for an invoice.
    If not yet analyzed, automatically triggers analysis and returns the report.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found.",
        )

    report = orchestrator.get_latest_analysis(invoice_id=invoice_id, db=db)
    if not report:
        # Run analysis on-demand if not already analyzed
        report = orchestrator.analyze_invoice(invoice_id=invoice_id, db=db)

    return report


@router.get("/logs/{invoice_id}", response_model=List[AgentExecutionLogResponse])
def get_invoice_agent_logs(
    invoice_id: int,
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieves execution history and audit logs for AI agents on a specific invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found.",
        )

    query = db.query(AgentExecutionLog).filter(AgentExecutionLog.invoice_id == invoice_id)
    if agent_name:
        query = query.filter(AgentExecutionLog.agent_name.ilike(f"%{agent_name}%"))

    return query.order_by(AgentExecutionLog.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/retry/{invoice_id}", response_model=MultiAgentAnalysisReport)
def retry_agent_analysis(invoice_id: int, db: Session = Depends(get_db)):
    """Retries multi-agent analysis safely and idempotently."""
    return run_agent_analysis(invoice_id=invoice_id, db=db)
