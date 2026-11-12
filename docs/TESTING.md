# Bahi-AI — Testing & Quality Assurance Documentation

This document describes the testing strategy, test suite architecture, automated test modules, financial regression cases, and execution instructions for **Bahi-AI** (University Accounts Payable Automation Agent).

---

## 1. Test Suite Overview

Bahi-AI employs a multi-tiered automated testing suite consisting of **70 Pytest integration and unit tests** covering all phases:

| Module | Test File | Test Count | Description |
|---|---|:---:|---|
| **Gemini Dynamic Orchestration** | `tests/test_gemini_orchestrator.py` | 14 | Provider initialization, API key sanitization, 13 backend tools, Pydantic validation, dynamic trajectory loop, loop detection, 8-call limit cap, prompt injection defense, financial safety guardrails, rule-based fallback, DB audit logging, and live integration |
| **Security & Auth** | `tests/test_security_audit.py` | 10 | Password verification, JWT validation, RBAC boundaries, path traversal defense, HTTP security headers, and regression invoice #9766 |
| **ERP & Accounting** | `tests/test_erp_accounting.py` | 10 | Double-entry balancing ($\sum Dr \equiv \sum Cr$), CGST/SGST/IGST tax allocations, penny rounding, reversals, posting eligibility, retry queues, and payment balance tracking |
| **Multi-Agent Automation** | `tests/test_multi_agent_automation.py` | 8 | Invoice Understanding, Vendor Verification, 3-Way Matching, Fraud & Risk Scoring, Approval Recommendation, and Orchestrator idempotency |
| **OCR & Regression** | `tests/test_ocr_accuracy_regression.py` | 7 | GST sample invoice parsing, CGST/SGST/IGST math, trade discount handling, low confidence flagging, and review synchronization |
| **Upload & Intake** | `tests/test_upload_and_ocr.py` | 9 | PDF/image upload validation, magic byte checks, 10MB file limit, SHA-256 duplicate detection, secure download, and human review validation |
| **Invoices Core** | `tests/test_invoices.py` | 5 | Health endpoints, executive dashboard summary, invoice listing, detail retrieval, and duplicate prevention |
| **Procurement & Matching** | `tests/test_matching.py` | 2 | Purchase orders, goods receipt notes (GRN), and fraud exception alerts |
| **Budgets & Depts** | `tests/test_budget.py` | 2 | Department cost centers, fiscal year budget allocations, and utilization tracking |
| **Authentication Core** | `tests/test_auth.py` | 2 | Argon2 password hashing and JWT token creation |
| **Workflow & Audit** | `tests/test_workflow.py` | 1 | Multi-level approval queuing, payment registry, and immutable audit logs |
| **Total** | | **70** | **100% Passed** |

---

## 2. Test Execution Instructions

### Prerequisites
- Python virtual environment activated: `cd backend && source .venv/bin/activate`
- PostgreSQL 16 container running: `docker compose up -d` (Port 5434)
- Alembic database schema migrated to head: `alembic upgrade head`

### Running the Full Test Suite
```bash
cd backend
.venv/bin/pytest tests/ -v
```

### Running Specific Test Categories
```bash
# Security & RBAC Suite
.venv/bin/pytest tests/test_security_audit.py -v

# ERP Ledger & Double-Entry Accounting
.venv/bin/pytest tests/test_erp_accounting.py -v

# Multi-Agent AI Orchestration
.venv/bin/pytest tests/test_multi_agent_automation.py -v

# OCR & GST Extraction Accuracy
.venv/bin/pytest tests/test_ocr_accuracy_regression.py -v
```

---

## 3. Financial Correctness & Invariance Tests

### Mathematical Invariance Rule:
Every double-entry journal entry must satisfy:
$$\sum \text{Debit Amount} \equiv \sum \text{Credit Amount}$$

### Known Regression Test Case (Invoice #9766):
A standard university vendor invoice fixture (`random_vendor_invoice.pdf`) is tested in `test_invoice_9766_financial_and_accounting_regression`:

- **Supplier:** Gupta Office Supplies
- **GSTIN:** 08HWZOU5586H5Z7
- **Taxable Subtotal:** ₹34,300.00
- **Input CGST (9%):** ₹3,087.00
- **Input SGST (9%):** ₹3,087.00
- **Total Tax:** ₹6,174.00
- **Grand Total:** ₹40,474.00

**Generated Journal Voucher Verification:**
- `DR 5003/5001` (Office Supplies & Operating Expenses): **₹34,300.00**
- `DR 1401` (Input Tax Credit — CGST): **₹3,087.00**
- `DR 1402` (Input Tax Credit — SGST): **₹3,087.00**
- `CR 2101` (Accounts Payable — Trade Creditors): **₹40,474.00**
- **Net Voucher Variance:** **₹0.00** (`is_balanced == True`)

---

## 4. Security & Access Control Verification

The automated security suite (`test_security_audit.py`) validates:
1. **Password Verification:** Argon2 hashing verification rejects malformed/incorrect passwords.
2. **JWT Authentication:** Valid tokens required for protected endpoints (`/api/v1/auth/me`).
3. **Role-Based Access Control (RBAC):**
   - Users with the `VENDOR` role are rejected with `HTTP 403 Forbidden` if attempting:
     - `POST /api/v1/approvals/{id}/action` (Invoice approval)
     - `POST /api/v1/erp/post/{id}` (ERP ledger posting)
     - `POST /api/v1/payments/{id}/simulate` (Payment settlement)
4. **Path Traversal Defense:** Calling `get_absolute_file_path` with directory escape sequences (`../../.env`, `/etc/passwd`) raises `PermissionError` and is strictly blocked.
5. **HTTP Security Headers:** Validates `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, and `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 5. Frontend Production Verification

```bash
cd frontend
npm run build
```
- Compiles all 20 static and dynamic routes.
- Enforces strict TypeScript 5 and ESLint rules.
- Validates that zero runtime exceptions occur during page generation.

