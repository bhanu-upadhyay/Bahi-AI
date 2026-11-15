"""
Database and Test Environment Isolation Safety Verification Test Suite for Bahi-AI.

Verifies:
1. Pytest runs strictly against 'bahi_ai_test' and never against the development database 'bahi_ai'.
2. Safety check raises RuntimeError if DATABASE_URL attempts to point to 'bahi_ai'.
3. Real invoice upload via FastAPI TestClient does NOT modify the development database.
4. Real duplicate invoice upload (fraud alert trigger) does NOT modify the development database.
5. Uploaded files are strictly contained within temporary test storage and never touch operational uploads.
"""

import io
import os
import urllib.parse
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.models import Invoice, FraudAlert, AgentExecutionLog
from app.utils.file_handler import BASE_UPLOAD_DIR, get_base_upload_dir

client = TestClient(app)


def get_dev_database_url() -> str:
    """Retrieves the development database URL from backend/.env for validation checks."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"
    raw_url = None
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    raw_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not raw_url:
        raw_url = "postgresql+psycopg://bahi_user:local_dev_password@localhost:5434/bahi_ai"
    return raw_url


def test_database_url_isolation():
    """Verify test DATABASE_URL points to bahi_ai_test and is strictly different from development."""
    current_test_url = settings.DATABASE_URL
    dev_url = get_dev_database_url()

    parsed_test = urllib.parse.urlparse(current_test_url)
    parsed_dev = urllib.parse.urlparse(dev_url)

    test_db_name = parsed_test.path.lstrip("/")
    dev_db_name = parsed_dev.path.lstrip("/")

    # Strict isolation assertions
    assert test_db_name == "bahi_ai_test", f"Test DB must be 'bahi_ai_test', got: {test_db_name}"
    assert dev_db_name == "bahi_ai", f"Dev DB must be 'bahi_ai', got: {dev_db_name}"
    assert current_test_url != dev_url, "CRITICAL: Test database URL equals development database URL!"
    assert test_db_name != dev_db_name, "CRITICAL: Test database name equals development database name!"


def test_safety_check_blocks_development_database():
    """Verify the safety validator raises RuntimeError if DATABASE_URL points to development."""
    from tests.conftest import pytest_configure

    class MockConfig:
        pass

    # Save current
    original_url = os.environ.get("DATABASE_URL")
    try:
        # Simulate someone pointing DATABASE_URL to bahi_ai
        os.environ["DATABASE_URL"] = "postgresql+psycopg://bahi_user:local_dev_password@localhost:5434/bahi_ai"
        with pytest.raises(RuntimeError) as exc_info:
            pytest_configure(MockConfig())
        assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)
        assert "bahi_ai" in str(exc_info.value)
    finally:
        # Restore test url
        if original_url:
            os.environ["DATABASE_URL"] = original_url


def test_invoice_upload_does_not_modify_development_database():
    """Verify that uploading an invoice via TestClient does NOT increase development database count."""
    dev_url = get_dev_database_url()
    dev_engine = create_engine(dev_url, pool_pre_ping=True)
    DevSession = sessionmaker(bind=dev_engine)

    # 1. Read baseline development count
    dev_db = DevSession()
    dev_inv_count_before = dev_db.query(Invoice).count()
    dev_db.close()

    # 2. Upload sample invoice PDF via FastAPI endpoint
    sample_pdf = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000119 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    )

    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("isolation_test_invoice.pdf", io.BytesIO(sample_pdf), "application/pdf")},
    )
    assert response.status_code == 201
    resp_data = response.json()
    assert "invoice_id" in resp_data
    assert resp_data["invoice_id"] is not None

    # 3. Verify development database invoice count is UNCHANGED
    dev_db2 = DevSession()
    dev_inv_count_after = dev_db2.query(Invoice).count()
    dev_db2.close()
    dev_engine.dispose()

    assert dev_inv_count_after == dev_inv_count_before, (
        f"LEAK DETECTED: Development invoice count changed from {dev_inv_count_before} to {dev_inv_count_after}!"
    )


def test_duplicate_invoice_does_not_create_development_fraud_alert():
    """Verify duplicate invoice upload creates alert in test session, but leaves dev alerts untouched."""
    dev_url = get_dev_database_url()
    dev_engine = create_engine(dev_url, pool_pre_ping=True)
    DevSession = sessionmaker(bind=dev_engine)

    # 1. Read baseline development fraud alert count
    dev_db = DevSession()
    dev_alerts_before = dev_db.query(FraudAlert).count()
    dev_db.close()

    # 2. Upload identical file twice in test client to trigger duplicate detection
    dup_pdf = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000119 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n% DUP_TEST_HASH_SALT_999"
    )

    res1 = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("dup_test_1.pdf", io.BytesIO(dup_pdf), "application/pdf")},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("dup_test_2.pdf", io.BytesIO(dup_pdf), "application/pdf")},
    )
    assert res2.status_code == 201
    assert res2.json()["processing_status"] == "DUPLICATE"

    # 3. Verify development fraud alerts count is UNCHANGED
    dev_db2 = DevSession()
    dev_alerts_after = dev_db2.query(FraudAlert).count()
    dev_db2.close()
    dev_engine.dispose()

    assert dev_alerts_after == dev_alerts_before, (
        f"LEAK DETECTED: Development fraud alerts changed from {dev_alerts_before} to {dev_alerts_after}!"
    )


def test_upload_storage_is_isolated():
    """Verify uploaded files are saved strictly to temporary test directory, not operational uploads."""
    backend_dir = Path(__file__).resolve().parent.parent
    operational_uploads_dir = (backend_dir / "uploads" / "invoices").resolve()
    active_test_upload_dir = get_base_upload_dir().resolve()

    # The active test upload directory must be temporary and NOT the operational upload directory
    assert active_test_upload_dir != operational_uploads_dir, (
        "CRITICAL: Active upload directory equals operational uploads directory!"
    )
    assert "bahi_test_uploads" in str(active_test_upload_dir) or "pytest" in str(active_test_upload_dir)

    # Perform upload
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
        b"?\x00\x05\xfe\x02\xfe\xa74e\xfe\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("storage_isolation.png", io.BytesIO(sample_png), "image/png")},
    )
    assert res.status_code == 201

    # Check file was written to temporary test directory
    test_files = list(active_test_upload_dir.glob("*.png"))
    assert len(test_files) >= 1
    for f in test_files:
        assert str(f.resolve()).startswith(str(active_test_upload_dir))
        assert not str(f.resolve()).startswith(str(operational_uploads_dir))

