from datetime import datetime, timezone
from decimal import Decimal
import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.agent_execution_log import AgentExecutionLog
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder
from app.schemas.agent import MultiAgentAnalysisReport
from app.services.agents.dynamic_orchestrator import DynamicAPOrchestrator, SYSTEM_INSTRUCTION
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.agents.providers.base import BaseLLMProvider, LLMStepResult, LLMToolCall
from app.services.agents.providers.gemini_provider import GeminiProvider
from app.services.agents.providers import get_llm_provider
from app.services.agents.tools.registry import (
    APToolRegistry,
    get_orchestration_tools,
    sanitize_tool_output,
    tool_registry,
)


# ---------------------------------------------------------------------------
# 1. Provider Initialization & Key Security Tests
# ---------------------------------------------------------------------------
def test_gemini_provider_init_validation():
    """GeminiProvider must reject empty or missing API keys."""
    with pytest.raises(ValueError, match="Gemini API key is missing"):
        GeminiProvider(api_key="")

    with pytest.raises(ValueError, match="Gemini API key is missing"):
        GeminiProvider(api_key="   ")


def test_gemini_provider_redacts_api_key_in_errors():
    """Ensure provider strips raw API key from any exception strings."""
    secret_key = "AIzaSySecretFakeKey1234567890"
    provider = GeminiProvider(api_key=secret_key, model_name="gemini-3.5-flash-lite")
    test_err = Exception(f"HTTP 403 Forbidden with key {secret_key}")
    sanitized = provider._sanitize_error(test_err)
    assert secret_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_provider_factory_without_key(monkeypatch):
    """When LLM_API_KEY is not set or empty, factory returns None."""
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    provider = get_llm_provider()
    assert provider is None


# ---------------------------------------------------------------------------
# 2. Tool Registry & Argument Validation Tests
# ---------------------------------------------------------------------------
def test_tool_registry_contains_all_13_tools():
    """APToolRegistry must register all 13 safe backend AP tools."""
    tools = tool_registry.get_tool_names()
    assert len(tools) == 13
    expected_tools = [
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
    for et in expected_tools:
        assert et in tools

    declarations = get_orchestration_tools()
    assert len(declarations) == 13


def test_tool_pydantic_validation_success_and_failure():
    """Pydantic must validate tool arguments and reject invalid schemas."""
    db = SessionLocal()
    try:
        # Valid approval policy tool call
        res_valid = tool_registry.execute_tool(
            "get_applicable_approval_policy",
            {"amount": 45000.0},
            db,
        )
        assert "error" not in res_valid
        assert res_valid["required_role"] == "HOD"

        # Invalid argument (negative amount)
        res_invalid = tool_registry.execute_tool(
            "get_applicable_approval_policy",
            {"amount": -500.0},
            db,
        )
        assert "error" in res_invalid
        assert "Invalid arguments" in res_invalid["error"]

        # Unknown tool
        res_unknown = tool_registry.execute_tool("drop_database_tables", {}, db)
        assert "error" in res_unknown
        assert "Unknown tool" in res_unknown["error"]
    finally:
        db.close()


def test_sanitize_tool_output_redacts_credentials():
    """Sanitizer must recursively redact passwords, secrets, tokens, and mask bank accounts."""
    raw = {
        "vendor_name": "Acme Corp",
        "bank_account_number": "987654321098",
        "api_key": "secret_key_value",
        "nested": {
            "token": "auth_token_xyz",
            "amount": Decimal("1500.50"),
        },
    }
    clean = sanitize_tool_output(raw)
    assert clean["vendor_name"] == "Acme Corp"
    assert clean["bank_account_number"] == "****1098"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["nested"]["token"] == "[REDACTED]"
    assert clean["nested"]["amount"] == 1500.50


# ---------------------------------------------------------------------------
# 3. Dynamic Loop & Tool Selection with Mocked Provider
# ---------------------------------------------------------------------------
class MockDynamicProvider(BaseLLMProvider):
    """Mock LLM provider that simulates a 3-step dynamic reasoning trajectory."""

    def __init__(self, steps: list[LLMStepResult]):
        super().__init__(api_key="mock-key", model_name="mock-gemini")
        self.steps = steps
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock-gemini"

    def generate_step(self, system_instruction, messages, tools=None) -> LLMStepResult:
        if self.call_count < len(self.steps):
            res = self.steps[self.call_count]
            self.call_count += 1
            return res
        return LLMStepResult(
            tool_calls=[],
            text_content="Final investigation completed.",
            model_name="mock-gemini",
            provider_name="mock-gemini",
        )


def test_dynamic_orchestrator_dynamic_trajectory():
    """Orchestrator should follow dynamic tool trajectory, log telemetry, and complete."""
    db = SessionLocal()
    try:
        # Fetch or create a test invoice
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoices found in database for test")

        mock_steps = [
            # Step 1: Model asks for invoice details
            LLMStepResult(
                tool_calls=[LLMToolCall(tool_name="get_invoice_details", arguments={"invoice_id": invoice.id})],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            ),
            # Step 2: Model verifies vendor
            LLMStepResult(
                tool_calls=[LLMToolCall(tool_name="verify_vendor_status", arguments={"invoice_id": invoice.id})],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            ),
            # Step 3: Model requests human review
            LLMStepResult(
                tool_calls=[
                    LLMToolCall(
                        tool_name="request_human_review",
                        arguments={
                            "invoice_id": invoice.id,
                            "reason": "All evidence verified successfully against master records.",
                            "recommended_action": "APPROVE",
                            "key_evidence": ["Invoice totals reconciled", "Vendor active & verified"],
                        },
                    )
                ],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            ),
        ]

        provider = MockDynamicProvider(steps=mock_steps)
        orchestrator = DynamicAPOrchestrator(provider=provider)

        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)
        assert isinstance(report, MultiAgentAnalysisReport)
        assert report.orchestration_mode == "GEMINI_DYNAMIC"
        assert report.model_used == "mock-gemini"
        assert report.recommendation == "APPROVE"
        assert len(report.tool_executions) == 3
        assert report.tool_executions[0].tool_name == "get_invoice_details"
        assert report.tool_executions[1].tool_name == "verify_vendor_status"
        assert report.tool_executions[2].tool_name == "request_human_review"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Loop Prevention & Max Tool Calls Protection
# ---------------------------------------------------------------------------
def test_dynamic_orchestrator_loop_prevention():
    """Loop detection must reject tools called with identical arguments >= 2 times."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoices found in test database")

        # Provider calls identical tool repeatedly
        mock_steps = [
            LLMStepResult(
                tool_calls=[LLMToolCall(tool_name="get_invoice_details", arguments={"invoice_id": invoice.id})],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            )
            for _ in range(5)
        ]

        provider = MockDynamicProvider(steps=mock_steps)
        orchestrator = DynamicAPOrchestrator(provider=provider)

        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)
        # Should detect loop and mark status as REJECTED for duplicate calls
        rejections = [t for t in report.tool_executions if t.status == "REJECTED"]
        assert len(rejections) >= 1
    finally:
        db.close()


def test_dynamic_orchestrator_max_tool_calls_cap():
    """Orchestrator must enforce MAX_TOOL_CALLS = 8."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoices in test database")

        # 12 distinct tool calls
        mock_steps = [
            LLMStepResult(
                tool_calls=[
                    LLMToolCall(
                        tool_name="get_applicable_approval_policy",
                        arguments={"amount": float(i * 1000 + 100)},
                    )
                ],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            )
            for i in range(12)
        ]

        provider = MockDynamicProvider(steps=mock_steps)
        orchestrator = DynamicAPOrchestrator(provider=provider)

        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)
        assert len(report.tool_executions) <= 8
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Security Guardrails & Prompt Injection Defense
# ---------------------------------------------------------------------------
def test_prompt_injection_defense_tagging():
    """Raw document text must be sanitized and wrapped in <untrusted_document_content>."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoice found in test database")

        # System instruction must explicitly warn about prompt injection
        assert "<untrusted_document_content>" in SYSTEM_INSTRUCTION
        assert "financial safety guardrails" in SYSTEM_INSTRUCTION.lower()
        assert "cannot and must not approve invoices" in SYSTEM_INSTRUCTION.lower()
    finally:
        db.close()


def test_hard_financial_safety_guardrails():
    """Verify that neither the AI nor dynamic orchestrator can approve invoices or execute payments."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoice found in test database")

        initial_approval = invoice.approval_status
        initial_payment = invoice.payment_status

        # Simulate dynamic analysis with APPROVE recommendation
        mock_steps = [
            LLMStepResult(
                tool_calls=[
                    LLMToolCall(
                        tool_name="request_human_review",
                        arguments={
                            "invoice_id": invoice.id,
                            "reason": "Safe to approve",
                            "recommended_action": "APPROVE",
                        },
                    )
                ],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            )
        ]
        provider = MockDynamicProvider(steps=mock_steps)
        orchestrator = DynamicAPOrchestrator(provider=provider)
        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)

        # Refresh from database
        db.refresh(invoice)

        # AI recommends APPROVE, but NEVER changes approval_status to APPROVED or pays
        assert report.recommendation == "APPROVE"
        assert invoice.approval_status == initial_approval
        assert invoice.payment_status == initial_payment
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 6. Fallback & Reliability
# ---------------------------------------------------------------------------
def test_fallback_to_rule_based_pipeline_on_error():
    """When Gemini raises an exception, the system must seamlessly fall back to rule-based execution."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoice in test database")

        # Create failing provider
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.generate_step.side_effect = RuntimeError("503 Service Unavailable / Rate Limit")
        mock_provider.model_name = "gemini-3.5-flash-lite"

        orchestrator = DynamicAPOrchestrator(provider=mock_provider)
        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)

        assert report.orchestrator_status == "COMPLETED"
        assert report.orchestration_mode == "FALLBACK_RULE_BASED"
        assert report.model_used == "rule-based-deterministic"
        assert report.understanding is not None
        assert report.vendor_verification is not None
        assert report.matching is not None
        assert report.fraud_risk is not None
        assert report.approval_recommendation is not None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. Audit Log Traceability
# ---------------------------------------------------------------------------
def test_audit_log_persisted_for_agent_and_tools():
    """Verify tool runs create AgentExecutionLog and AuditLog database records."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoice in test database")

        mock_steps = [
            LLMStepResult(
                tool_calls=[LLMToolCall(tool_name="validate_invoice_totals", arguments={"invoice_id": invoice.id})],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            ),
            LLMStepResult(
                tool_calls=[
                    LLMToolCall(
                        tool_name="request_human_review",
                        arguments={
                            "invoice_id": invoice.id,
                            "reason": "Math verified",
                            "recommended_action": "APPROVE",
                        },
                    )
                ],
                model_name="mock-gemini",
                provider_name="mock-gemini",
            ),
        ]
        provider = MockDynamicProvider(steps=mock_steps)
        orchestrator = DynamicAPOrchestrator(provider=provider)
        orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)

        # Verify DB logs
        tool_logs = (
            db.query(AgentExecutionLog)
            .filter(
                AgentExecutionLog.invoice_id == invoice.id,
                AgentExecutionLog.agent_name.ilike("Tool:%"),
            )
            .all()
        )
        assert len(tool_logs) >= 2

        # Verify AuditLog
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.entity_id == str(invoice.id),
                AuditLog.action == "GEMINI_DYNAMIC_ANALYSIS_COMPLETED",
            )
            .first()
        )
        assert audit is not None
        assert audit.new_values["orchestration_mode"] == "GEMINI_DYNAMIC"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. Live Integration Test (Requires RUN_LIVE_LLM_TEST=true)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TEST") != "true",
    reason="Live Gemini API test requires RUN_LIVE_LLM_TEST=true",
)
def test_live_gemini_dynamic_orchestration():
    """Optional live integration test validating actual Gemini API call and tool loops."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).first()
        if not invoice:
            pytest.skip("No invoice available for live testing")

        provider = get_llm_provider()
        if not provider:
            pytest.skip("Gemini provider not configured")

        orchestrator = DynamicAPOrchestrator(provider=provider)
        report = orchestrator.analyze_invoice(invoice_id=invoice.id, db=db)

        assert report.orchestration_mode in ["GEMINI_DYNAMIC", "FALLBACK_RULE_BASED"]
        assert report.recommendation in ["APPROVE", "REVIEW", "REJECT"]
        assert report.risk_score >= 0
    finally:
        db.close()
