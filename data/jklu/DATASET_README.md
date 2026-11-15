# JKLU University AP Synthetic Dataset (v1.1.0)

**Institution:** JK Lakshmipat University (Jaipur, Rajasthan)  
**Location:** Near Mahindra World City, P.O. Mahapura, Ajmer Road, Jaipur, Rajasthan 302026  
**State Code:** 08 (Rajasthan)  
**GSTIN:** 08AAACJ0001Z1Z0  
**Reference Simulation Date:** 2026-11-15  

---

## 1. Overview & Purpose

This dataset provides a production-grade, interconnected university Accounts Payable (AP) synthetic dataset designed for demonstration, benchmarking, and automated testing of **Bahi-AI** at the **JKLU AI Buildathon**.

### Implemented Fixes in v1.1.0:
- **FIX 1:** Completely eliminated duplicate PO (`PO-JKLU-2026-001`) and GRN (`GRN-JKLU-2026-001`) entries. Scenario 5 (duplicate invoice) now cleanly references Scenario 1's PO and GRN without entity duplication.
- **FIX 2:** Multi-line invoice expansion: increased from 19 to **42 invoice lines**, **32 PO lines**, and **32 GRN lines**, fulfilling the multi-line volume target.
- **FIX 3:** Scenario 15 includes an unlisted accessory line item (Calibration Probe Kit) not on the PO, ensuring `ThreeWayMatchingAgent` triggers `DISCREPANCY` deterministically.
- **FIX 4:** Scenario 9 preserves the intended 12% vs 18% statutory tax rate variance without introducing artificial arithmetic errors.
- **FIX 5:** Clean scenarios use synthetic Rajasthan vendors (`VND-JKLU-09` and `VND-JKLU-10`) with matching Indian GSTINs, achieving clean `VERIFIED` and `APPROVE` outcomes.
