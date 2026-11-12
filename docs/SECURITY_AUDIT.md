# Bahi-AI — Security Audit & Threat Assessment Report

This document records the security audit, vulnerability analysis, hardening measures, and residual risk assessment performed on **Bahi-AI** (University Accounts Payable Automation Agent).

---

## 1. Executive Summary

A comprehensive application security audit was conducted covering the FastAPI backend, Next.js frontend, database layer, authentication protocols, and file-handling pipelines. The application is designed for an academic prototype demonstrating university accounts payable automation with mock ERP integration.

| Security Domain | Status | Key Safeguards Implemented |
|---|:---:|---|
| **Password Security** | **PASS** | Argon2id multi-pass cryptographic hashing via `pwdlib` |
| **Session Management** | **PASS** | Signed JSON Web Tokens (HS256) with 60-minute expiration |
| **Access Control (RBAC)** | **PASS** | Strict role-based boundaries on sensitive financial mutations |
| **Filesystem & Uploads** | **PASS** | Magic-byte signature inspection, 10MB limit, strict uploads-root sandboxing |
| **SQL Injection** | **PASS** | Parameterized SQLAlchemy 2.0 ORM queries across all endpoints |
| **HTTP Security Headers** | **PASS** | Nosniff, Frame-Options DENY, XSS-Protection, Referrer-Policy |
| **Financial Guardrails** | **PASS** | Mandatory human approval, strict voucher balancing, overpayment blocking |

---

## 2. Vulnerability Assessment & Hardening Actions

### Finding 1: Unmounted Auth Router & Missing Login Endpoints
- **Severity:** Medium (Prototype Access)
- **Observation:** While JWT generation and password hashing helpers were present, the FastAPI API router had an empty `auth.py` file with no mounted `/api/v1/auth/login` endpoint.
- **Resolution:** Implemented `/api/v1/auth/login`, `/api/v1/auth/me`, and `/api/v1/auth/logout` in `app/api/routes/auth.py`. Validates email/password against stored Argon2 hashes, enforces active status, generates signed JWT bearer tokens, and records audit trail events.

### Finding 2: Missing Role-Based Authorization on Sensitive Actions
- **Severity:** High (Privilege Escalation Risk)
- **Observation:** Invoices could previously be approved or posted to ERP without validating that the authenticated user possessed an appropriate administrative or finance role.
- **Resolution:** Introduced `require_roles(*allowed_roles)` dependency in `app/core/dependencies.py`:
  - `POST /api/v1/approvals/{id}/action`: Restricted to `FINANCE_ADMIN`, `FINANCE_OFFICER`, and `HOD`.
  - `POST /api/v1/erp/post/{id}`: Restricted to `FINANCE_ADMIN` and `FINANCE_OFFICER`.
  - `POST /api/v1/payments/prepare` and `simulate`: Restricted to `FINANCE_ADMIN` and `FINANCE_OFFICER`.
  - Rejection with `HTTP 403 Forbidden` verified via automated tests when called with a `VENDOR` role token.

### Finding 3: Path Traversal in Document Path Resolution
- **Severity:** High (Information Disclosure)
- **Observation:** `get_absolute_file_path()` in `app/utils/file_handler.py` only checked if the resolved path was inside the root `backend/` directory, which could theoretically allow reading non-upload files (e.g. `.env`) if a document path was manipulated.
- **Resolution:** Hardened `get_absolute_file_path()` to:
  1. Reject explicit directory escape sequences (`..`) and null bytes (`\x00`).
  2. Enforce that all resolved document paths must reside strictly within `backend/uploads/`.
  3. Verified via automated test `test_path_traversal_prevention`.

### Finding 4: Missing HTTP Security Headers
- **Severity:** Low (Defense in Depth)
- **Observation:** API responses did not supply standard browser defense headers.
- **Resolution:** Added HTTP middleware in `app/main.py` setting:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### Finding 5: Gitignore & Database Dump Protection
- **Severity:** Medium (Accidental Data Leakage)
- **Observation:** Database backup dumps (`backups/` and `*.sql`) were present in the workspace and not explicitly ignored in `.gitignore`.
- **Resolution:** Added `backups/`, `*.sql`, and `*.dump` to `.gitignore`. Empty root `.env.example` was populated with placeholder configurations only.

---

## 3. Financial Integrity & Invariance Guardrails

1. **Double-Entry Equilibrium:**
   $$\sum \text{Debits} == \sum \text{Credits}$$
   The accounting engine enforces exact mathematical balance down to the penny. Fractional rounding variances are allocated to Account `5099`.
2. **Overpayment Prevention:**
   Disbursement preparation verifies that requested payment amount $\le \text{Outstanding Invoice Balance}$. Overpayments are blocked with `HTTP 400 Bad Request`.
3. **Idempotent ERP Posting:**
   A SHA-256 idempotency key is computed from invoice parameters. Replayed requests return the existing posting record without generating duplicate journal entries or duplicate ERP records.
4. **Non-Autonomous Financial Policy:**
   AI agent recommendations (`APPROVE`, `REVIEW`, `REJECT`) are advisory only. No invoice is ever auto-approved or automatically posted to the general ledger without human officer action.

---

## 4. Residual Risks & Academic Prototype Scope

- **Mock ERP & Simulated Disbursements:** The application connects to a simulated University ERP adapter and mock payment orchestrator. No real banking or production SAP/Oracle integration is enabled.
- **Single-Host Sandbox:** Both frontend and backend run on local loopback (`localhost:3000` / `localhost:8000`). Production deployment would require SSL/TLS termination (HTTPS), rate limiting (e.g. Redis-backed slowapi), and a managed secret vault (AWS Secrets Manager / GCP Secret Manager).
- **Disclaimer:** This audit validates controls against project requirements for academic demonstration; it does not constitute a certified commercial SOC-2 or ISO-27001 assessment.
