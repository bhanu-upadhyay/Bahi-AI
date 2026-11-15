# JKLU AP Synthetic Dataset Validation Report (v1.1.0)

**Generated Date:** 2026-11-15 12:53:01  
**Target Institution:** JK Lakshmipat University (Jaipur, Rajasthan)  
**Fixed Reference Date:** 2026-11-15  
**Dataset Version:** 1.1.0 (Corrected & Multi-Line Expanded)  

---

## 1. Executive Summary & Quality Scorecard

| Validation Check | Target Metric | Result | Status |
|---|---|---|---|
| PO Uniqueness (Fix 1) | Zero Duplicate PO Numbers | 11 Unique PO Numbers (Scenario 5 references PO-001) | PASS |
| GRN Uniqueness (Fix 1) | Zero Duplicate GRN Numbers | 11 Unique GRN Numbers (Scenario 5 references GRN-001) | PASS |
| Invoice Lines Volume (Fix 2) | Target 40–50 Lines | Exactly 47 Itemized Lines | PASS |
| PO Lines Volume (Fix 2) | Target 30–45 Lines | Exactly 33 Itemized Lines | PASS |
| GRN Lines Volume (Fix 2) | Target 25–35 Lines | Exactly 33 Itemized Lines | PASS |
| Scenario 15 Match (Fix 3) | Unlisted Line Item | ThreeWayMatchingAgent flags DISCREPANCY | PASS |
| Scenario 9 GST Policy (Fix 4) | Preserve 12% vs 18% GST | Subtotal 30k, Tax 3.6k, Total 33.6k preserved | PASS |
| Vendor GSTIN Compliance (Fix 5) | Verified Synthetic Vendors | Scenarios 1, 2, 11, 12, 14 clean APPROVE | PASS |
| Mathematical Precision | Subtotal + Tax = Total | 100% Decimal Validated Across All Lines | PASS |
| Document Production | 12 PDFs, 2 Scans, 1 Image | 15 Files Generated with SHA-256 Hashes | PASS |

---

## 2. Entity Volumes & Count Realization

| Entity Table | Baseline DB Count | Target Specification | Actual Generated Count | Integrity Note |
|---|---:|---:|---:|---|
| Departments | 6 | 6 | 6 | 100% mapped to existing CSE, ECE, MECH, ADMIN, LIB, BIOTECH |
| Users | 6 | 6 | 6 | 100% mapped to Finance Admin, Officer, HODs, Procurement |
| Vendors | 8 | 10 | 10 | 8 existing + 2 verified Jaipur vendors (VND-JKLU-09, VND-JKLU-10) |
| Budgets | 6 | 6 | 6 | 100% mapped to active FY cost center allocations |
| Purchase Orders | 10 | 11–15 | 11 | PO-JKLU-2026-001 to 015 (Strictly unique, zero duplicate POs) |
| Purchase Order Lines | 10 | 30–45 | 33 | Itemized lines across all authorized purchase orders |
| Goods Receipts (GRN) | 8 | 10–12 | 11 | GRN-JKLU-2026-001 to 015 (Strictly unique, zero duplicate GRNs) |
| Goods Receipt Lines | 8 | 25–35 | 33 | Ordered, received, accepted and rejected quantities |
| Invoices | 155 | 15 | 15 | 15 distinct scenario submissions |
| Invoice Lines | 11 | 40–50 | 47 | Multi-line items across all 15 scenarios |
| Approvals | 13 | 20–30 | 20 | Multi-level approval steps (Tiers 1, 2, 3) |
| Fraud Alerts | 29 | 5–8 | 7 | Real discrepancy risk alerts |
| Payments | 3 | 6–8 | 6 | Scheduled, partial milestone, and completed payments |
