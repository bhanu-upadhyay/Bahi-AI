"""
Global Pytest Configuration and Test Database Isolation for Bahi-AI.

Enforces strict isolation rules:
1. Pytest MUST NEVER connect to or execute against the development database ('bahi_ai').
2. Pytest automatically points DATABASE_URL to 'bahi_ai_test'.
3. Every test runs within a nested transaction (SAVEPOINT) that is automatically rolled back
   at test teardown, ensuring zero persistent test mutations in the test database.
4. Document uploads in tests are routed to an isolated temporary directory, ensuring zero
   pollution of the operational uploads/ directory.
"""

import os
import shutil
import urllib.parse
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# -----------------------------------------------------------------------------
# 1. Early Environment Initialization (Prior to importing FastAPI / Settings)
# -----------------------------------------------------------------------------

def _resolve_test_db_url() -> str:
    """Derives the dedicated test database URL from environment or .env."""
    backend_dir = Path(__file__).resolve().parent.parent
    env_file = backend_dir / ".env"

    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url and env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    raw_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not raw_url:
        raw_url = "postgresql+psycopg://bahi_user:local_dev_password@localhost:5434/bahi_ai"

    parsed = urllib.parse.urlparse(raw_url)
    path = parsed.path
    if not path.endswith("_test"):
        test_path = "/bahi_ai_test"
    else:
        test_path = path

    return urllib.parse.urlunparse(parsed._replace(path=test_path))


TEST_DATABASE_URL = _resolve_test_db_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"

# Clear settings cache so it loads the new DATABASE_URL
from app.core.config import get_settings
get_settings.cache_clear()

from app.core.database import Base, get_db
import app.core.database as db_module
from app.main import app
from app.utils import file_handler

# Create dedicated test engine
test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


def _sync_test_db_sequences(engine):
    """Ensures test database sequences are synchronized with max table IDs."""
    from sqlalchemy import text
    tables = [
        "invoices", "invoice_lines", "vendors", "departments",
        "purchase_orders", "purchase_order_lines", "goods_receipts",
        "goods_receipt_lines", "approvals", "payments", "fraud_alerts",
        "audit_logs", "agent_execution_logs", "journal_entries", "journal_entry_lines",
    ]
    with engine.begin() as conn:
        for tbl in tables:
            try:
                conn.execute(
                    text(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE((SELECT MAX(id) FROM {tbl}), 1))")
                )
            except Exception:
                pass


# -----------------------------------------------------------------------------
# 2. Strict Pytest Configuration Hook (Fail if pointing to development)
# -----------------------------------------------------------------------------

def pytest_configure(config):
    """Fails pytest immediately if DATABASE_URL points to the development database."""
    current_url = os.environ.get("DATABASE_URL", "")
    parsed = urllib.parse.urlparse(current_url)
    db_name = parsed.path.lstrip("/")

    if db_name == "bahi_ai" or db_name.endswith("/bahi_ai") or not db_name.endswith("_test"):
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: pytest is configured to run against the development database '{db_name}'. "
            f"Pytest must run strictly against a dedicated test database (e.g. 'bahi_ai_test'). Current URL: {current_url}"
        )

    _sync_test_db_sequences(test_engine)


# -----------------------------------------------------------------------------
# 3. Test Fixtures: Database Rollback & Upload Storage Isolation
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_upload_storage(tmp_path_factory, monkeypatch):
    """Isolates file upload storage to a temporary directory for each test run."""
    temp_dir = tmp_path_factory.mktemp("bahi_test_uploads")
    monkeypatch.setenv("UPLOAD_DIR", str(temp_dir))
    monkeypatch.setattr(file_handler, "BASE_UPLOAD_DIR", temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def db_session(monkeypatch):
    """Wraps each test in an isolated connection with savepoint rollback.
    
    Any commits inside application routes only release the savepoint;
    the outer transaction is unconditionally rolled back on test teardown.
    """
    connection = test_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    # Override FastAPI dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(db_module, "SessionLocal", lambda: Session(bind=connection, join_transaction_mode="create_savepoint"))

    yield session

    app.dependency_overrides.clear()
    session.close()
    trans.rollback()
    connection.close()

