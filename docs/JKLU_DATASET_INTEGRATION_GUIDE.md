# Bahi-AI — JKLU Synthetic AP Dataset Integration Guide

## 1. Overview & Architectural Context

This guide documents the synthetic Accounts Payable (AP) production-grade dataset created for **JK Lakshmipat University (JKLU)** in Jaipur, Rajasthan, for the **JKLU AI Buildathon**.

The dataset provides 15 realistic, interconnected university AP scenarios reflecting actual university procurement:
- Departmental operational supplies & printing
- Computer laboratory hardware & cloud transit slices
- Mechanical engineering & robotics workshop tooling
- Campus facilities, HVAC chiller servicing & executive furniture
- Central library subscriptions, books & archival scanners
- Biotechnology assay reagents & laboratory glassware

All financial values are calculated in **Indian Rupees (INR)** adhering strictly to the **Indian Goods and Services Tax (GST)** statutory framework (Rajasthan State Code `08`).

---

## 2. Directory Structure

```
data/jklu/
├── DATASET_README.md                  # Comprehensive dataset overview & scenario matrix
├── DATA_VALIDATION_REPORT.md          # Integrity report (math, GST, FKs, OCR metrics)
├── JKLU_AP_Dataset.json               # Full JSON dataset of all entities & relations
├── SCENARIO_EXPECTATIONS.json         # Automated verification expectations per scenario
├── JKLU_AP_Dataset.xlsx               # Professional multi-sheet Excel workbook (18 sheets)
├── generate_dataset.py                # Standalone generator utility
└── invoices/                          # 15 synthetic invoice documents & manifest
    ├── INVOICE_MANIFEST.json          # File metadata, SHA256 hashes, and target extraction fields
    ├── INV-JKLU-2026-001.pdf          # Scenario 1: Clean 3-way match (Digital PDF)
    ├── INV-JKLU-2026-002.pdf          # Scenario 2: Partial goods delivery (Digital PDF)
    ├── INV-JKLU-2026-003.pdf          # Scenario 3: Price variance / rate markup (Digital PDF)
    ├── INV-JKLU-2026-004.pdf          # Scenario 4: Quantity variance / rejected stock (Digital PDF)
    ├── INV-JKLU-2026-005.pdf          # Scenario 5: Duplicate invoice collision (Digital PDF)
    ├── INV-JKLU-2026-006.pdf          # Scenario 6: Unregistered emergency vendor (Digital PDF)
    ├── INV-JKLU-2026-007.pdf          # Scenario 7: Non-PO direct operational spend (Digital PDF)
    ├── INV-JKLU-2026-008.pdf          # Scenario 8: Department budget exceeded (Digital PDF)
    ├── INV-JKLU-2026-009.pdf          # Scenario 9: GST rate math discrepancy (Digital PDF)
    ├── INV-JKLU-2026-010.pdf          # Scenario 10: Suspicious fraud signals (Digital PDF)
    ├── INV-JKLU-2026-011.pdf          # Scenario 11: Partially paid milestone license (Scanned PDF)
    ├── INV-JKLU-2026-012.pdf          # Scenario 12: Overdue facilities invoice (Scanned PDF)
    ├── INV-JKLU-2026-013.pdf          # Scenario 13: Inter-state supply with 100% IGST (Digital PDF)
    ├── INV-JKLU-2026-014.pdf          # Scenario 14: Multi-tax rate schedule (5%, 12%, 18%) (Digital PDF)
    └── INV-JKLU-2026-015.png          # Scenario 15: Conflicting model specifications (Image PNG)
```

---

## 3. Entity Relationships & Foreign Key Hierarchy

The dataset maintains relational integrity across 12 database tables:

```
[Departments (1-6)] <----+ [Users (1-6)]
       ^                  |       ^
       |                  |       |
[Budgets (1-6)]           |       +---------------+
       ^                  |                       |
       |                  v                       v
[Vendors (1-10)] ---> [Purchase Orders] ---> [Goods Receipts]
       |                  | (15 POs)              | (12 GRNs)
       |                  v                       v
       |              [PO Lines] <----------- [GRN Lines]
       |                  | (35 lines)            | (28 lines)
       |                  |                       |
       v                  v                       v
  [Invoices (15)] <-------+-----------------------+
       | (42 lines)
       +---> [Invoice Lines]
       +---> [Approvals (22 workflows across Tiers 1-3)]
       +---> [Fraud Alerts (7 automated anomaly detections)]
       +---> [Payments (7 scheduled/completed disbursements)]
```

### Reference Conventions:
- **Reference Simulation Date:** `2026-11-15`
- **Institution State:** Rajasthan (`08`)
- **Intra-State GST:** 50% Input CGST (Account 1401) + 50% Input SGST (Account 1402)
- **Inter-State GST:** 100% Input IGST (Account 1403) for non-Rajasthan vendors (Delhi `07`, Karnataka `29`)

---

## 4. Safe Database Importer Instructions

The safe database importer is located at:
`backend/app/scripts/import_jklu_dataset.py`

### Safety Guarantees:
1. **Append-Only:** Never deletes, truncates, or resets existing database records or sequences.
2. **Idempotent:** Detects and skips existing PO numbers, GRN numbers, invoice numbers, and payment references.
3. **Foreign Key Integrity:** Reuses existing departments (1–6), users (1–6), and budgets (1–6).
4. **Transaction Safe:** Uses atomic transaction blocks with rollback on error.
5. **No Fake Execution Logs:** Does not insert fabricated AI execution logs or operational ERP postings.

### Step 1: Run Dry-Run Mode (Zero Database Writes)
```bash
PYTHONPATH=backend backend/.venv/bin/python backend/app/scripts/import_jklu_dataset.py --dry-run
```

Expected output:
- Resolves all 6 existing departments and 6 users.
- Matches 8 existing vendors and stages 2 new Rajasthan vendors (`VND-JKLU-09`, `VND-JKLU-10`).
- Validates 12 POs, 12 GRNs, 15 Invoices, 20 Approvals, 7 Fraud Alerts, 6 Payments.
- Performs immediate transaction rollback: **Zero database rows modified**.

### Step 2: Live Import Execution (Authorized by Administrator)
```bash
PYTHONPATH=backend backend/.venv/bin/python backend/app/scripts/import_jklu_dataset.py --execute
```

---

## 5. Testing the 15 Scenarios

### Method A: Automated Pytest Suite
Run the dedicated JKLU dataset test suite:
```bash
backend/.venv/bin/pytest backend/tests/test_jklu_dataset.py -v
```
Validates:
- Relational integrity across all 12 tables.
- Decimal-safe mathematical reconciliation (Subtotal + Tax = Total).
- Statutory GST tax split logic (CGST/SGST vs IGST).
- Document presence and OCR extraction accuracy on all 15 files.
- Double-entry accounting balance on illustrative journal vouchers.

### Method B: End-to-End Workflow via Bahi-AI Web Interface
1. **Start Backend & Frontend:**
   ```bash
   # Terminal 1: Backend
   cd backend && PYTHONPATH=. .venv/bin/uvicorn app.main:app --port 8000 --reload
   
   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```
2. **Access Web Application:**
   Open `http://localhost:3000` in browser.
3. **Upload an Invoice Document:**
   - Navigate to `/invoices/upload`.
   - Drag and drop any generated document from `data/jklu/invoices/` (e.g. `INV-JKLU-2026-001.pdf`).
   - Observe automatic PyMuPDF / Tesseract extraction: Invoice number, vendor GSTIN, line items, and totals extract with high confidence.
4. **Trigger AI Multi-Agent Analysis:**
   - Click "Run Multi-Agent Analysis" on the invoice detail page (`/invoices/{id}`).
   - The 5 agents evaluate the invoice:
     - **Invoice Understanding Agent:** Validates financial mathematics and line-item totals.
     - **Vendor Verification Agent:** Verifies vendor master record, active status, and matching GSTIN.
     - **Three-Way Matching Agent:** Compares invoice lines against authorized PO lines and warehouse GRN accepted receipts.
     - **Fraud & Risk Agent:** Calculates risk score (0-100) and identifies specific policy risk factors.
     - **Approval Recommendation Agent:** Emits formal recommendation (`APPROVE`, `REVIEW`, `REJECT`) and routes to the appropriate approval tier.
5. **Approve & Post to Accounting:**
   - Authorized users approve clean invoices.
   - Click "Generate Journal Voucher" to create double-entry journal vouchers (Debiting expense & tax accounts, Crediting Accounts Payable 2101).
   - Click "Post to ERP" to trigger simulated SAP/Oracle ERP integration with idempotency protection.

---

## 6. Scenario Expectations Matrix

| Scenario | File | Match Status | Risk Level | Approval Rec | Payment Status | Key Reason |
|---|---|---|---|---|---|---|
| **1. Clean Match** | `INV-JKLU-2026-001.pdf` | `FULL_MATCH` | LOW (0) | APPROVE (Tier 2) | SCHEDULED | Exact PO/GRN match, verified vendor, within Tier 2 FO authority. |
| **2. Partial Delivery** | `INV-JKLU-2026-002.pdf` | `PARTIAL_MATCH` | LOW (0) | APPROVE (Tier 2) | SCHEDULED | 30/60 delivered; invoice strictly bills accepted 30 units. |
| **3. Price Variance** | `INV-JKLU-2026-003.pdf` | `PRICE_VARIANCE` | MEDIUM (30) | REVIEW (Tier 1) | UNPAID | Unit price ₹2,100 exceeds PO rate ₹1,800 (+₹300/unit markup). |
| **4. Quantity Overbilling** | `INV-JKLU-2026-004.pdf` | `QUANTITY_VARIANCE` | HIGH (40) | REVIEW (Tier 2) | UNPAID | 5 damaged chairs rejected by warehouse; billed for all 25. |
| **5. Duplicate Submission** | `INV-JKLU-2026-005.pdf` | `FULL_MATCH` | CRITICAL (75) | REJECT (Tier 3) | CANCELLED | Duplicate invoice collision against registered invoice. |
| **6. Unregistered Vendor** | `INV-JKLU-2026-006.pdf` | `NO_PO` | MEDIUM (40) | REVIEW (Tier 1) | UNPAID | Vendor not registered in vendor master; onboarding required. |
| **7. Non-PO Direct Spend** | `INV-JKLU-2026-007.pdf` | `NO_PO` | LOW (15) | REVIEW (Tier 1) | UNPAID | Operational hackathon bandwidth spend; requires HOD sign-off. |
| **8. Budget Exceeded** | `INV-JKLU-2026-008.pdf` | `FULL_MATCH` | LOW (0) | REVIEW (Tier 3) | UNPAID | Dept 5 available budget ₹80k vs invoice ₹100.3k (deficit ₹20.3k). |
| **9. GST Math Error** | `INV-JKLU-2026-009.pdf` | `FULL_MATCH` | HIGH (30) | REVIEW (Tier 1) | UNPAID | Applied 12% GST instead of statutory 18% (discrepancy ₹1,800). |
| **10. Suspicious Submission**| `INV-JKLU-2026-010.pdf` | `NO_PO` | HIGH (60) | REJECT (Tier 3) | CANCELLED | Generic sequence 9999, high value non-PO spend, bank mismatch. |
| **11. Milestone Payment** | `INV-JKLU-2026-011.pdf` | `FULL_MATCH` | LOW (0) | APPROVE (Tier 2) | PARTIAL | ₹70,800 paid advance; balance ₹70,800 outstanding. |
| **12. Overdue Invoice** | `INV-JKLU-2026-012.pdf` | `FULL_MATCH` | LOW (0) | APPROVE (Tier 1) | SCHEDULED | Billed 01-Oct with Net 30 terms; 15 days overdue on 15-Nov. |
| **13. Inter-State Supply** | `INV-JKLU-2026-013.pdf` | `FULL_MATCH` | LOW (0) | APPROVE (Tier 2) | SCHEDULED | Delhi vendor (07) allocates 100% IGST (Account 1403). |
| **14. Multi-Tax Rates** | `INV-JKLU-2026-014.pdf` | `FULL_MATCH` | LOW (0) | APPROVE (Tier 2) | SCHEDULED | Mixed 5%, 12%, and 18% tax rates on distinct lines. |
| **15. Conflicting Specs** | `INV-JKLU-2026-015.png` | `DISCREPANCY` | MEDIUM (30) | REVIEW (Tier 2) | UNPAID | 200MHz oscilloscope supplied instead of 100MHz PO spec. |

---

## 7. Rollback & Database Recovery Procedure

If a database restore is ever required:
1. **Container Re-launch:**
   ```bash
   docker-compose up -d postgres
   ```
2. **Seed Baseline Data:**
   ```bash
   PYTHONPATH=backend backend/.venv/bin/python backend/app/scripts/seed_demo_data.py
   ```
3. **Verify Integrity:**
   ```bash
   backend/.venv/bin/pytest backend/tests/ -v
   ```

