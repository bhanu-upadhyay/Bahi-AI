"""
Test Suite for JKLU AP Importer Database Safety Guard.

Verifies strict safety guarantees:
1. --execute against 'bahi_ai' (development) is strictly blocked.
2. --execute against 'bahi_ai_test' (automated test DB) is strictly blocked.
3. --execute against 'bahi_ai_demo' is allowed past the guard.
4. Dry-run mode is permitted across environments and strictly performs ZERO database commits.
5. No bypass flags (e.g., --allow-any-db) can circumvent the database restrictions.
"""

from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from app.models import (
    Approval,
    Budget,
    Department,
    FraudAlert,
    GoodsReceipt,
    Invoice,
    InvoiceLine,
    Payment,
    PurchaseOrder,
    User,
    Vendor,
)
from app.scripts.import_jklu_dataset import (
    DEMO_DATABASE_NAME,
    JKLUDataSetImporter,
    resolve_target_database,
    validate_target_database,
)


def _create_mock_session_with_db_name(db_name: str) -> MagicMock:
    """Creates a mock SQLAlchemy session whose engine URL resolves to db_name."""
    mock_session = MagicMock(spec=Session)
    mock_bind = MagicMock()
    mock_bind.url.database = db_name
    mock_session.get_bind.return_value = mock_bind
    return mock_session


# -----------------------------------------------------------------------------
# 1. Blocked Execution Tests: bahi_ai (Development)
# -----------------------------------------------------------------------------

def test_execute_against_bahi_ai_is_blocked():
    """Verify that --execute (dry_run=False) against development DB 'bahi_ai' is strictly blocked."""
    mock_db = _create_mock_session_with_db_name("bahi_ai")

    assert resolve_target_database(mock_db) == "bahi_ai"

    # Direct validation function must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        validate_target_database(mock_db, dry_run=False)

    error_message = str(exc_info.value)
    assert "CRITICAL SAFETY VIOLATION" in error_message
    assert "bahi_ai" in error_message
    assert "bahi_ai_demo" in error_message

    # Instantiating importer with dry_run=False must also fail immediately on the guard
    with pytest.raises(RuntimeError) as exc_info_importer:
        JKLUDataSetImporter(mock_db, dry_run=False)

    assert "CRITICAL SAFETY VIOLATION" in str(exc_info_importer.value)


# -----------------------------------------------------------------------------
# 2. Blocked Execution Tests: bahi_ai_test (Test Database)
# -----------------------------------------------------------------------------

def test_execute_against_bahi_ai_test_is_blocked(db_session: Session):
    """Verify that --execute (dry_run=False) against test DB 'bahi_ai_test' is strictly blocked."""
    actual_test_db = resolve_target_database(db_session)
    assert actual_test_db == "bahi_ai_test", f"Expected bahi_ai_test, got: {actual_test_db}"

    # Direct validation function must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        validate_target_database(db_session, dry_run=False)

    error_message = str(exc_info.value)
    assert "CRITICAL SAFETY VIOLATION" in error_message
    assert "bahi_ai_test" in error_message
    assert "bahi_ai_demo" in error_message

    # Instantiating importer with dry_run=False against live test DB must fail on guard
    with pytest.raises(RuntimeError) as exc_info_importer:
        JKLUDataSetImporter(db_session, dry_run=False)

    assert "CRITICAL SAFETY VIOLATION" in str(exc_info_importer.value)


# -----------------------------------------------------------------------------
# 3. Permitted Execution Test: bahi_ai_demo (Demo Database)
# -----------------------------------------------------------------------------

def test_execute_against_bahi_ai_demo_is_allowed_past_guard():
    """Verify that --execute (dry_run=False) against 'bahi_ai_demo' passes the safety guard."""
    mock_demo_db = _create_mock_session_with_db_name(DEMO_DATABASE_NAME)

    # Database name must resolve to bahi_ai_demo
    assert resolve_target_database(mock_demo_db) == "bahi_ai_demo"

    # Must pass validation without raising RuntimeError
    validated_db = validate_target_database(mock_demo_db, dry_run=False)
    assert validated_db == "bahi_ai_demo"

    # Importer instantiation must succeed and record target_db without raising RuntimeError
    importer = JKLUDataSetImporter(mock_demo_db, dry_run=False)
    assert importer.target_db == "bahi_ai_demo"
    assert importer.dry_run is False


# -----------------------------------------------------------------------------
# 4. Dry-Run Zero DB Mutation Test
# -----------------------------------------------------------------------------

def test_dry_run_does_not_commit_changes(db_session: Session):
    """
    Verify that running the importer in dry-run mode against bahi_ai_test:
    1. Passes database validation and records target database.
    2. Performs simulated validation without error.
    3. Leaves entity table row counts 100% unchanged (Zero DB writes).
    """
    # 1. Capture table row counts before dry-run
    counts_before = {
        "departments": db_session.query(Department).count(),
        "users": db_session.query(User).count(),
        "vendors": db_session.query(Vendor).count(),
        "budgets": db_session.query(Budget).count(),
        "purchase_orders": db_session.query(PurchaseOrder).count(),
        "goods_receipts": db_session.query(GoodsReceipt).count(),
        "invoices": db_session.query(Invoice).count(),
        "invoice_lines": db_session.query(InvoiceLine).count(),
        "fraud_alerts": db_session.query(FraudAlert).count(),
        "payments": db_session.query(Payment).count(),
    }

    # 2. Run importer in dry-run mode
    importer = JKLUDataSetImporter(db_session, dry_run=True)
    assert importer.target_db == "bahi_ai_test"

    result = importer.run()

    assert result["dry_run"] is True
    assert result["target_db"] == "bahi_ai_test"
    assert "stats" in result

    # 3. Capture table row counts after dry-run
    counts_after = {
        "departments": db_session.query(Department).count(),
        "users": db_session.query(User).count(),
        "vendors": db_session.query(Vendor).count(),
        "budgets": db_session.query(Budget).count(),
        "purchase_orders": db_session.query(PurchaseOrder).count(),
        "goods_receipts": db_session.query(GoodsReceipt).count(),
        "invoices": db_session.query(Invoice).count(),
        "invoice_lines": db_session.query(InvoiceLine).count(),
        "fraud_alerts": db_session.query(FraudAlert).count(),
        "payments": db_session.query(Payment).count(),
    }

    # 4. Assert strict zero-mutation guarantee
    for entity, count in counts_before.items():
        assert counts_after[entity] == count, (
            f"Table '{entity}' was mutated in dry-run mode! "
            f"Before: {count}, After: {counts_after[entity]}"
        )


# -----------------------------------------------------------------------------
# 5. Guard Immutability: No Bypass Allowed
# -----------------------------------------------------------------------------

def test_no_bypass_allowed():
    """Verify that validate_target_database accepts no bypass flags or arguments."""
    import inspect
    sig = inspect.signature(validate_target_database)
    # The signature must only have db and dry_run parameters
    param_names = list(sig.parameters.keys())
    assert param_names == ["db", "dry_run"], f"Unexpected parameters in safety guard: {param_names}"


def test_cli_rejects_bypass_argument():
    """Verify that the CLI parser rejects --allow-any-db flag."""
    import sys
    from unittest.mock import patch
    from app.scripts.import_jklu_dataset import main

    test_args = ["import_jklu_dataset.py", "--execute", "--allow-any-db"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            main()


def test_cli_execute_blocked_on_non_demo_db():
    """Verify that invoking main() with --execute on non-demo DB raises RuntimeError before processing."""
    import sys
    from unittest.mock import patch
    from app.scripts.import_jklu_dataset import main

    # Under pytest, DATABASE_URL points to bahi_ai_test
    test_args = ["import_jklu_dataset.py", "--execute"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(RuntimeError) as exc_info:
            main()

    assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)
    assert "bahi_ai_test" in str(exc_info.value)
