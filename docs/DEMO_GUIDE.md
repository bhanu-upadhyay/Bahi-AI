# Bahi-AI — University Evaluator Demonstration Guide

This guide provides an end-to-end walkthrough for demonstrating **Bahi-AI** to university evaluators, academic committees, and finance stakeholders.

---

## 1. Demo Credentials & User Roles

You can sign in via `/login` or use the role switcher in the top-right header:

| Email | Role | Department | Default Password |
|---|---|---|---|
| `sarah.jenkins@university.edu` | **Finance Admin** | Central Finance & AP | `BahiAI@2025!` |
| `robert.vance@university.edu` | **Finance Officer** | Accounts Payable | `BahiAI@2025!` |
| `marcus.chen@university.edu` | **Procurement Officer** | Central Procurement | `BahiAI@2025!` |
| `alan.turing@university.edu` | **HOD** | Computer Science & Eng. | `BahiAI@2025!` |
| `nikola.tesla@university.edu` | **HOD** | Electrical Engineering | `BahiAI@2025!` |
| `accounts@apexcomputing.demo` | **Vendor Representative** | Apex Computing Solutions | `BahiAI@2025!` |

---

## 2. 15-Step Evaluator Walkthrough

### Step 1: Sign In & Role Initialization
- Open `http://localhost:3000/login`
- Enter `sarah.jenkins@university.edu` and password `BahiAI@2025!`.
- Alternatively, click the role switcher in the top navigation bar to select **Finance Admin**.

### Step 2: Executive AP Dashboard
- Navigate to `/dashboard`
- Highlight the **Executive AP Overview**:
  - Total invoices processed, pending approval count, active exception alerts.
  - Department budget utilization bars across academic faculties.
  - Recent audit trail entries reflecting live actions.

### Step 3: Document Upload & Intake Guardrails
- Navigate to `/invoices/upload`
- Drag and drop or browse to upload an invoice document:
  - You can use the provided fixture: `backend/tests/fixtures/random_vendor_invoice.pdf`
- Explain the security guardrails:
  - Magic-byte inspection validates true PDF / image signatures.
  - 10 MB file size limit and path traversal protections.
  - Immediate SHA-256 duplicate detection if uploading an existing file.

### Step 4: OCR & Field Extraction
- Observe automatic text extraction and structured parsing:
  - Extracted Vendor Name, GSTIN, Invoice Number, Invoice Date, Subtotal, CGST, SGST, IGST, and Total.
  - Visual extraction confidence score (e.g., 95%).

### Step 5: Invoice Detail & Live Math Reconciliation
- Click into the uploaded or existing invoice at `/invoices/1`.
- Point out the **Financial Math Reconciliation Banner**:
  - Live verification: $\text{Taxable Subtotal} + \text{Total Tax} \equiv \text{Grand Total}$.
  - Color-coded indicator: Emerald (Reconciled) or Amber (Discrepancy).

### Step 6: 5-Agent AI Automation Hub
- On the invoice detail page, view the **Multi-Agent AI Automation Hub**:
  1. **Invoice Understanding Agent:** Evaluates subtotal, taxes, and extraction abnormalities.
  2. **Vendor Verification Agent:** Validates registered status in University Vendor Master.
  3. **Three-Way Matching Agent:** Cross-references PO and GRN lines.
  4. **Fraud & Risk Scoring Agent:** Assigns a risk score (0–100) and flags overbilling.
  5. **Approval Recommendation Agent:** Synthesizes policy action (`APPROVE`, `REVIEW`, `REJECT`).
- Highlight that the AI provides recommendations but **never approves invoices automatically**.

### Step 7: Three-Way Match Verification
- Navigate to `/matching`
- Review how line items are compared across the three core procurement records:
  - **Invoice Lines** vs **Purchase Order Lines** vs **Goods Receipt Accepted Quantities**.
  - Strict 0.00% unit price variance and zero over-delivery allowance.

### Step 8: Fraud & Exception Center
- Navigate to `/fraud`
- Show flagged exception types:
  - `OVERBILLING_DETECTED` (Invoice amount exceeds authorized PO).
  - `DUPLICATE_INVOICE` (Exact file hash or vendor/invoice number collision).
  - `PRICE_VARIANCE` and `UNAPPROVED_VENDOR`.

### Step 9: Human Officer Approval Workflow
- Navigate to `/approvals`
- Select a pending invoice and click **Approve** or **Reject** with comments.
- **RBAC Demonstration:** Switch user role to `Vendor Representative` and demonstrate that the vendor is forbidden (`HTTP 403`) from approving invoices.

### Step 10: ERP Posting Eligibility Gates
- Return to the approved invoice detail page (`/invoices/1`).
- Scroll to the **Phase 4: ERP Integration & Accounting Posting Panel**.
- Review the **7 Eligibility Gates**:
  - Human Officer Approval: `PASSED`
  - Non-Duplicate Posting: `PASSED`
  - Reconciled Financial Totals: `PASSED`
  - Active Vendor in Master: `PASSED`
  - Department Cost Center: `PASSED`
  - Chart of Accounts Mapped: `PASSED`
  - Currency & Bank Details: `PASSED`

### Step 11: Post to Mock University ERP
- In the posting panel, review the live **Journal Voucher Preview**.
- Click **"Post to Mock University ERP"**.
- Observe simulated latency (150ms) and generation of university ERP document reference:
  - `UERP-2026-INV-XXXX`.
  - Invoice status automatically updates to `POSTED`.

### Step 12: General Ledger & Double-Entry Accounting
- Navigate to `/ledger`
- View the **Journal Entries Registry**:
  - Balanced vouchers where $\sum \text{Debit} == \sum \text{Credit}$.
  - Department Operating Expense (`5001`/`5003`) debited.
  - Input CGST (`1401`) and Input SGST (`1402`) debited.
  - Accounts Payable Trade Creditors (`2101`) credited.
- Click any entry to open the interactive **Journal Entry Detail Modal** with reversal capability.

### Step 13: Trial Balance Verification
- In `/ledger`, click the **Trial Balance** tab.
- Confirm zero net variance:
  - Total Debits = Total Credits.
  - Net Variance = **₹0.00** (`ZERO VARIANCE CONFIRMED`).

### Step 14: Payment Management & Settlement
- Navigate to `/payments`
- Click **"Prepare Disbursement"** to open the payment drawer:
  - Select an approved invoice.
  - Review live balance: Total Invoiced, Already Settled, Outstanding Balance.
  - Enter a partial payment amount (e.g., ₹20,000 of ₹40,474).
  - Select method (ACH, Wire, Check) and schedule.
- In the table, click **"Simulate Settlement"**:
  - Payment settles with confirmation timestamp.
  - Invoice payment status automatically updates from `UNPAID` $\to$ `PARTIAL`.
  - Settle remaining balance to see status transition to `PAID`.

### Step 15: System Audit Trail
- Navigate to `/audit`
- Demonstrate the immutable, append-only audit trail logging every user login, OCR run, agent evaluation, human approval decision, ERP posting, and simulated settlement.
