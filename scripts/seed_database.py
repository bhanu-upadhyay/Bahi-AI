#!/usr/bin/env python3
"""
Bahi-AI Database Seed Script (Idempotent)
Populates the database with realistic demonstration data for university accounts payable:
- 6 University Departments
- 8 Approved Vendors
- 6 Users across all roles (VENDOR, HOD, PROCUREMENT_OFFICER, FINANCE_OFFICER, FINANCE_ADMIN)
- 10 Purchase Orders with line items
- 8 Goods Receipts with line items (supporting partial deliveries)
- 11 Invoices with line items covering all scenarios:
  * Normal matched invoice (approved & paid)
  * Approved invoice awaiting payment
  * Awaiting HOD approval
  * Duplicate invoice flagged with fraud alert
  * Invoice exceeding PO amount (overbilling alert)
  * Invoice with quantity mismatch (invoiced > received)
  * Invoice with missing goods receipt
  * Invoice exceeding department budget
  * Invoice under review
  * In-process matching invoice
  * Newly received invoice
- Fiscal year budgets
- Multi-level approvals
- Fraud alerts with risk scores
- Payment records
- Complete audit logs and agent execution logs
"""

import sys
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models import (
    Department,
    User,
    UserRole,
    Vendor,
    PurchaseOrder,
    PurchaseOrderLine,
    GoodsReceipt,
    GoodsReceiptLine,
    Invoice,
    InvoiceLine,
    normalize_invoice_number,
    Budget,
    Approval,
    Payment,
    FraudAlert,
    AuditLog,
    AgentExecutionLog,
)


def seed_database():
    db = SessionLocal()
    try:
        print("🌱 Starting idempotent database seeding for Bahi-AI...")

        # -------------------------------------------------------------
        # 1. Departments
        # -------------------------------------------------------------
        departments_data = [
            {"code": "CSE", "name": "Computer Science & Engineering", "description": "Academic department for computing and AI labs"},
            {"code": "ECE", "name": "Electrical & Electronics Engineering", "description": "Academic department for robotics and circuits"},
            {"code": "MECH", "name": "Mechanical Engineering", "description": "Academic department for manufacturing and thermodynamics"},
            {"code": "ADMIN", "name": "Campus Facilities & Operations", "description": "University administration, operations and physical infrastructure"},
            {"code": "LIB", "name": "Central Library & Digital Archives", "description": "University repository, journal subscriptions and digital library"},
            {"code": "BIOTECH", "name": "Biotechnology & Life Sciences", "description": "Genetics and medical research laboratories"},
        ]

        departments = {}
        for dept_dict in departments_data:
            existing = db.query(Department).filter_by(code=dept_dict["code"]).first()
            if not existing:
                existing = Department(**dept_dict)
                db.add(existing)
                db.flush()
                print(f"  + Added Department: {existing.name} ({existing.code})")
            departments[existing.code] = existing

        # -------------------------------------------------------------
        # 2. Users (5 Roles)
        # -------------------------------------------------------------
        default_pwd_hash = get_password_hash("BahiAI@2025!")
        users_data = [
            {
                "full_name": "Dr. Sarah Jenkins",
                "email": "sarah.jenkins@university.edu",
                "role": UserRole.FINANCE_ADMIN.value,
                "department_id": departments["ADMIN"].id,
            },
            {
                "full_name": "Robert Vance",
                "email": "robert.vance@university.edu",
                "role": UserRole.FINANCE_OFFICER.value,
                "department_id": departments["ADMIN"].id,
            },
            {
                "full_name": "Marcus Chen",
                "email": "marcus.chen@university.edu",
                "role": UserRole.PROCUREMENT_OFFICER.value,
                "department_id": departments["ADMIN"].id,
            },
            {
                "full_name": "Prof. Alan Turing",
                "email": "alan.turing@university.edu",
                "role": UserRole.HOD.value,
                "department_id": departments["CSE"].id,
            },
            {
                "full_name": "Prof. Nikola Tesla",
                "email": "nikola.tesla@university.edu",
                "role": UserRole.HOD.value,
                "department_id": departments["ECE"].id,
            },
            {
                "full_name": "Alex Rivera",
                "email": "accounts@apexcomputing.demo",
                "role": UserRole.VENDOR.value,
                "department_id": None,
            },
        ]

        users = {}
        for user_dict in users_data:
            existing = db.query(User).filter_by(email=user_dict["email"]).first()
            if not existing:
                existing = User(
                    full_name=user_dict["full_name"],
                    email=user_dict["email"],
                    password_hash=default_pwd_hash,
                    role=user_dict["role"],
                    department_id=user_dict["department_id"],
                    is_active=True,
                )
                db.add(existing)
                db.flush()
                print(f"  + Added User: {existing.full_name} ({existing.role})")
            users[existing.email] = existing

        # -------------------------------------------------------------
        # 3. Department Budgets (FY 2024-2025)
        # -------------------------------------------------------------
        fiscal_year = "2024-2025"
        budgets_data = [
            {"dept": "CSE", "allocated": Decimal("250000.00"), "committed": Decimal("80000.00"), "spent": Decimal("45000.00"), "available": Decimal("125000.00")},
            {"dept": "ECE", "allocated": Decimal("180000.00"), "committed": Decimal("30000.00"), "spent": Decimal("25000.00"), "available": Decimal("125000.00")},
            {"dept": "MECH", "allocated": Decimal("220000.00"), "committed": Decimal("40000.00"), "spent": Decimal("35000.00"), "available": Decimal("145000.00")},
            {"dept": "ADMIN", "allocated": Decimal("500000.00"), "committed": Decimal("95000.00"), "spent": Decimal("110000.00"), "available": Decimal("295000.00")},
            {"dept": "LIB", "allocated": Decimal("120000.00"), "committed": Decimal("22000.00"), "spent": Decimal("18000.00"), "available": Decimal("80000.00")},
            {"dept": "BIOTECH", "allocated": Decimal("150000.00"), "committed": Decimal("15000.00"), "spent": Decimal("12000.00"), "available": Decimal("123000.00")},
        ]

        for b_data in budgets_data:
            dept = departments[b_data["dept"]]
            existing_b = db.query(Budget).filter_by(department_id=dept.id, fiscal_year=fiscal_year).first()
            if not existing_b:
                existing_b = Budget(
                    department_id=dept.id,
                    fiscal_year=fiscal_year,
                    allocated_amount=b_data["allocated"],
                    committed_amount=b_data["committed"],
                    spent_amount=b_data["spent"],
                    available_amount=b_data["available"],
                )
                db.add(existing_b)
                db.flush()
                print(f"  + Added Budget: {dept.code} FY {fiscal_year}")

        # -------------------------------------------------------------
        # 4. Vendors (8 Vendors)
        # -------------------------------------------------------------
        vendors_data = [
            {
                "vendor_code": "VND-TECH-01",
                "legal_name": "Apex Computing Solutions Inc.",
                "contact_person": "Alex Rivera",
                "email": "accounts@apexcomputing.demo",
                "phone": "+1-555-019-2831",
                "address": "400 Tech Boulevard, Suite 500, Austin, TX 78701",
                "tax_identifier": "US-EIN-74-3928172",
                "bank_account_last_four": "9812",
                "bank_name": "Silicon Valley Commercial Bank",
            },
            {
                "vendor_code": "VND-LAB-02",
                "legal_name": "Quantum Scientific Instruments LLC",
                "contact_person": "Dr. Brenda Zhao",
                "email": "sales@quantumsci.demo",
                "phone": "+1-555-014-9921",
                "address": "1200 Precision Way, Boston, MA 02115",
                "tax_identifier": "US-EIN-04-8837192",
                "bank_account_last_four": "4431",
                "bank_name": "First New England Bank",
            },
            {
                "vendor_code": "VND-PUB-03",
                "legal_name": "ScholarPress Academic Publications Ltd",
                "contact_person": "Graham Stewart",
                "email": "billing@scholarpress.demo",
                "phone": "+1-555-018-7264",
                "address": "88 Academic Circle, Oxford, CT 06478",
                "tax_identifier": "US-EIN-06-2910482",
                "bank_account_last_four": "1098",
                "bank_name": "Colonial Federal Union",
            },
            {
                "vendor_code": "VND-OFF-04",
                "legal_name": "Horizon Campus Supplies & Furnishings",
                "contact_person": "David Miller",
                "email": "support@horizoncampus.demo",
                "phone": "+1-555-013-4412",
                "address": "55 Logistics Parkway, Columbus, OH 43215",
                "tax_identifier": "US-EIN-31-9018273",
                "bank_account_last_four": "7720",
                "bank_name": "Midwest Commerce Bank",
            },
            {
                "vendor_code": "VND-NET-05",
                "legal_name": "Optima High-Speed Fiber Networks",
                "contact_person": "Priya Nair",
                "email": "orders@optimafiber.demo",
                "phone": "+1-555-017-5509",
                "address": "770 Gigabit Lane, Reston, VA 20190",
                "tax_identifier": "US-EIN-54-3819204",
                "bank_account_last_four": "6329",
                "bank_name": "Capital Tech Union",
            },
            {
                "vendor_code": "VND-FAC-06",
                "legal_name": "BlueSky Environmental & Facilities Services",
                "contact_person": "Thomas Bradley",
                "email": "service@blueskyfac.demo",
                "phone": "+1-555-012-3390",
                "address": "900 Industrial Ave, Chicago, IL 60607",
                "tax_identifier": "US-EIN-36-7712940",
                "bank_account_last_four": "8814",
                "bank_name": "Great Lakes National Bank",
            },
            {
                "vendor_code": "VND-CHEM-07",
                "legal_name": "BioPure Reagents & Chemicals Co.",
                "contact_person": "Elena Rostova",
                "email": "orders@biopurelab.demo",
                "phone": "+1-555-019-4822",
                "address": "330 Bio Parkway, San Diego, CA 92121",
                "tax_identifier": "US-EIN-95-6628193",
                "bank_account_last_four": "2054",
                "bank_name": "Pacific Coast Union",
            },
            {
                "vendor_code": "VND-SOFT-08",
                "legal_name": "DataLogic Enterprise AI Software Corp.",
                "contact_person": "Jonathan Vance",
                "email": "enterprise@datalogicai.demo",
                "phone": "+1-555-011-8840",
                "address": "100 Cloud Summit Plaza, Seattle, WA 98101",
                "tax_identifier": "US-EIN-91-4401928",
                "bank_account_last_four": "5512",
                "bank_name": "Evergreen State Bank",
            },
        ]

        vendors = {}
        for v_dict in vendors_data:
            existing = db.query(Vendor).filter_by(vendor_code=v_dict["vendor_code"]).first()
            if not existing:
                existing = Vendor(**v_dict, is_active=True)
                db.add(existing)
                db.flush()
                print(f"  + Added Vendor: {existing.legal_name} ({existing.vendor_code})")
            vendors[existing.vendor_code] = existing

        # -------------------------------------------------------------
        # 5. Purchase Orders (10 POs with Line Items)
        # -------------------------------------------------------------
        creator = users["marcus.chen@university.edu"]
        today = date.today()

        pos_data = [
            {
                "po_number": "PO-2024-001",
                "vendor_code": "VND-TECH-01",
                "dept_code": "CSE",
                "issue_date": today - timedelta(days=45),
                "delivery_date": today - timedelta(days=25),
                "total_amount": Decimal("35400.00"),
                "tax_amount": Decimal("5400.00"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "High-Performance AI Compute Workstations (RTX 4090)", "quantity": Decimal("10.00"), "unit_price": Decimal("3000.00"), "tax_rate": Decimal("18.00"), "total": Decimal("35400.00")}
                ],
            },
            {
                "po_number": "PO-2024-002",
                "vendor_code": "VND-TECH-01",
                "dept_code": "CSE",
                "issue_date": today - timedelta(days=35),
                "delivery_date": today - timedelta(days=15),
                "total_amount": Decimal("9600.00"),
                "tax_amount": Decimal("1464.41"),
                "status": "PARTIALLY_DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "UltraSharp 27-inch 4K Developer Displays", "quantity": Decimal("24.00"), "unit_price": Decimal("338.98"), "tax_rate": Decimal("18.00"), "total": Decimal("9600.00")}
                ],
            },
            {
                "po_number": "PO-2024-003",
                "vendor_code": "VND-LAB-02",
                "dept_code": "ECE",
                "issue_date": today - timedelta(days=40),
                "delivery_date": today - timedelta(days=20),
                "total_amount": Decimal("14800.00"),
                "tax_amount": Decimal("2257.63"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "Digital Storage 4-Channel Oscilloscopes 200MHz", "quantity": Decimal("4.00"), "unit_price": Decimal("3135.59"), "tax_rate": Decimal("18.00"), "total": Decimal("14800.00")}
                ],
            },
            {
                "po_number": "PO-2024-004",
                "vendor_code": "VND-PUB-03",
                "dept_code": "LIB",
                "issue_date": today - timedelta(days=30),
                "delivery_date": today - timedelta(days=10),
                "total_amount": Decimal("12750.00"),
                "tax_amount": Decimal("721.70"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "Advanced Deep Learning & Systems Textbooks (Vol 1-3)", "quantity": Decimal("150.00"), "unit_price": Decimal("80.19"), "tax_rate": Decimal("6.00"), "total": Decimal("12750.00")}
                ],
            },
            {
                "po_number": "PO-2024-005",
                "vendor_code": "VND-LAB-02",
                "dept_code": "MECH",
                "issue_date": today - timedelta(days=20),
                "delivery_date": today - timedelta(days=5),
                "total_amount": Decimal("18200.00"),
                "tax_amount": Decimal("2776.27"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "CNC 5-Axis Milling Machine Laser Calibration Unit", "quantity": Decimal("1.00"), "unit_price": Decimal("15423.73"), "tax_rate": Decimal("18.00"), "total": Decimal("18200.00")}
                ],
            },
            {
                "po_number": "PO-2024-006",
                "vendor_code": "VND-OFF-04",
                "dept_code": "ADMIN",
                "issue_date": today - timedelta(days=25),
                "delivery_date": today - timedelta(days=8),
                "total_amount": Decimal("22400.00"),
                "tax_amount": Decimal("3416.95"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "Ergonomic Lumbar Executive Task Chairs", "quantity": Decimal("80.00"), "unit_price": Decimal("237.29"), "tax_rate": Decimal("18.00"), "total": Decimal("22400.00")}
                ],
            },
            {
                "po_number": "PO-2024-007",
                "vendor_code": "VND-FAC-06",
                "dept_code": "ADMIN",
                "issue_date": today - timedelta(days=15),
                "delivery_date": today - timedelta(days=2),
                "total_amount": Decimal("16500.00"),
                "tax_amount": Decimal("2516.95"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "Annual Central HVAC Diagnostic & Air Filter Maintenance", "quantity": Decimal("1.00"), "unit_price": Decimal("13983.05"), "tax_rate": Decimal("18.00"), "total": Decimal("16500.00")}
                ],
            },
            {
                "po_number": "PO-2024-008",
                "vendor_code": "VND-NET-05",
                "dept_code": "CSE",
                "issue_date": today - timedelta(days=18),
                "delivery_date": today - timedelta(days=4),
                "total_amount": Decimal("28900.00"),
                "tax_amount": Decimal("4408.47"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "Enterprise 48-Port 10Gbps Managed SFP+ Switches", "quantity": Decimal("4.00"), "unit_price": Decimal("6122.88"), "tax_rate": Decimal("18.00"), "total": Decimal("28900.00")}
                ],
            },
            {
                "po_number": "PO-2024-009",
                "vendor_code": "VND-CHEM-07",
                "dept_code": "BIOTECH",
                "issue_date": today - timedelta(days=12),
                "delivery_date": today + timedelta(days=7),
                "total_amount": Decimal("8400.00"),
                "tax_amount": Decimal("1024.00"),
                "status": "ISSUED",
                "lines": [
                    {"line_number": 1, "description": "Molecular Biology PCR Reagents & Assay Buffers Batch", "quantity": Decimal("20.00"), "unit_price": Decimal("368.80"), "tax_rate": Decimal("14.00"), "total": Decimal("8400.00")}
                ],
            },
            {
                "po_number": "PO-2024-010",
                "vendor_code": "VND-SOFT-08",
                "dept_code": "CSE",
                "issue_date": today - timedelta(days=10),
                "delivery_date": today - timedelta(days=1),
                "total_amount": Decimal("15000.00"),
                "tax_amount": Decimal("2288.14"),
                "status": "DELIVERED",
                "lines": [
                    {"line_number": 1, "description": "100-Seat Academic Simulation Software Enterprise License", "quantity": Decimal("1.00"), "unit_price": Decimal("12711.86"), "tax_rate": Decimal("18.00"), "total": Decimal("15000.00")}
                ],
            },
        ]

        purchase_orders = {}
        po_lines_map = {}

        for p_dict in pos_data:
            existing = db.query(PurchaseOrder).filter_by(po_number=p_dict["po_number"]).first()
            if not existing:
                existing = PurchaseOrder(
                    po_number=p_dict["po_number"],
                    vendor_id=vendors[p_dict["vendor_code"]].id,
                    department_id=departments[p_dict["dept_code"]].id,
                    issue_date=p_dict["issue_date"],
                    expected_delivery_date=p_dict["delivery_date"],
                    total_amount=p_dict["total_amount"],
                    tax_amount=p_dict["tax_amount"],
                    status=p_dict["status"],
                    created_by=creator.id,
                )
                db.add(existing)
                db.flush()
                for line_dict in p_dict["lines"]:
                    p_line = PurchaseOrderLine(
                        purchase_order_id=existing.id,
                        line_number=line_dict["line_number"],
                        item_description=line_dict["description"],
                        quantity=line_dict["quantity"],
                        unit_price=line_dict["unit_price"],
                        tax_rate=line_dict["tax_rate"],
                        total_amount=line_dict["total"],
                    )
                    db.add(p_line)
                    db.flush()
                print(f"  + Added PO: {existing.po_number} (${existing.total_amount})")
            purchase_orders[existing.po_number] = existing
            po_lines_map[existing.po_number] = existing.lines

        # -------------------------------------------------------------
        # 6. Goods Receipts (8 GRNs, supporting partial deliveries)
        # -------------------------------------------------------------
        receiver = users["marcus.chen@university.edu"]
        grns_data = [
            {
                "grn_number": "GRN-2024-001",
                "po_number": "PO-2024-001",
                "received_date": today - timedelta(days=24),
                "status": "RECEIVED",
                "notes": "All 10 workstations unboxed, serial numbers verified and bench tested by lab manager.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("10.00"), "received": Decimal("10.00"), "accepted": Decimal("10.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-002",
                "po_number": "PO-2024-002",
                "received_date": today - timedelta(days=14),
                "status": "PARTIAL",
                "notes": "Partial shipment arrived: 20 monitors received in good order. 4 backordered by vendor.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("24.00"), "received": Decimal("20.00"), "accepted": Decimal("20.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-003",
                "po_number": "PO-2024-003",
                "received_date": today - timedelta(days=19),
                "status": "RECEIVED",
                "notes": "4 oscilloscopes received with NIST calibration certificates.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("4.00"), "received": Decimal("4.00"), "accepted": Decimal("4.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-004",
                "po_number": "PO-2024-004",
                "received_date": today - timedelta(days=9),
                "status": "RECEIVED",
                "notes": "150 engineering textbooks received and cataloged by central library staff.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("150.00"), "received": Decimal("150.00"), "accepted": Decimal("150.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-005",
                "po_number": "PO-2024-005",
                "received_date": today - timedelta(days=4),
                "status": "RECEIVED",
                "notes": "Laser calibration unit tested on 5-axis CNC mill with workshop technician.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("1.00"), "received": Decimal("1.00"), "accepted": Decimal("1.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-006",
                "po_number": "PO-2024-006",
                "received_date": today - timedelta(days=7),
                "status": "PARTIAL",
                "notes": "80 task chairs delivered. 60 accepted in good shape. 20 rejected with broken hydraulic cylinders.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("80.00"), "received": Decimal("80.00"), "accepted": Decimal("60.00"), "rejected": Decimal("20.00")}],
            },
            {
                "grn_number": "GRN-2024-007",
                "po_number": "PO-2024-007",
                "received_date": today - timedelta(days=2),
                "status": "INSPECTED",
                "notes": "HVAC service sign-off complete. Air quality sensors validated across Buildings A, B, and C.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("1.00"), "received": Decimal("1.00"), "accepted": Decimal("1.00"), "rejected": Decimal("0.00")}],
            },
            {
                "grn_number": "GRN-2024-008",
                "po_number": "PO-2024-008",
                "received_date": today - timedelta(days=3),
                "status": "RECEIVED",
                "notes": "4x 10G switches received and rack-mounted in Core Data Center Server Room 102.",
                "lines": [{"po_line_idx": 0, "ordered": Decimal("4.00"), "received": Decimal("4.00"), "accepted": Decimal("4.00"), "rejected": Decimal("0.00")}],
            },
        ]

        goods_receipts = {}
        for g_dict in grns_data:
            existing = db.query(GoodsReceipt).filter_by(grn_number=g_dict["grn_number"]).first()
            if not existing:
                po = purchase_orders[g_dict["po_number"]]
                existing = GoodsReceipt(
                    grn_number=g_dict["grn_number"],
                    purchase_order_id=po.id,
                    received_by=receiver.id,
                    received_date=g_dict["received_date"],
                    status=g_dict["status"],
                    notes=g_dict["notes"],
                )
                db.add(existing)
                db.flush()
                for line_spec in g_dict["lines"]:
                    po_line = po_lines_map[g_dict["po_number"]][line_spec["po_line_idx"]]
                    grn_line = GoodsReceiptLine(
                        goods_receipt_id=existing.id,
                        purchase_order_line_id=po_line.id,
                        quantity_ordered=line_spec["ordered"],
                        quantity_received=line_spec["received"],
                        quantity_accepted=line_spec["accepted"],
                        quantity_rejected=line_spec["rejected"],
                    )
                    db.add(grn_line)
                    db.flush()
                print(f"  + Added Goods Receipt: {existing.grn_number} for {po.po_number}")
            goods_receipts[existing.grn_number] = existing

        # -------------------------------------------------------------
        # 7. Invoices (11 Invoices covering all required scenarios)
        # -------------------------------------------------------------
        invoices_data = [
            # Scenario 1: Normal invoice, matched, fully approved and paid
            {
                "invoice_number": "INV-2024-001",
                "vendor_code": "VND-TECH-01",
                "po_number": "PO-2024-001",
                "dept_code": "CSE",
                "invoice_date": today - timedelta(days=22),
                "due_date": today + timedelta(days=8),
                "subtotal": Decimal("30000.00"),
                "tax_amount": Decimal("5400.00"),
                "total_amount": Decimal("35400.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "MATCHED",
                "approval_status": "APPROVED",
                "payment_status": "PAID",
                "lines": [{"desc": "High-Performance AI Compute Workstations (RTX 4090)", "qty": Decimal("10.00"), "unit_price": Decimal("3000.00"), "tax": Decimal("18.00"), "total": Decimal("35400.00")}],
                "approvals": [
                    {"approver": "alan.turing@university.edu", "level": 1, "status": "APPROVED", "comments": "Workstations verified in AI Lab 304. Approved for payment."},
                    {"approver": "sarah.jenkins@university.edu", "level": 2, "status": "APPROVED", "comments": "Three-way match verified. Approved from CSE hardware capital fund."},
                ],
                "payment": {"ref": "PAY-2024-001", "date": today - timedelta(days=5), "amount": Decimal("35400.00"), "method": "ACH", "status": "COMPLETED"},
                "fraud_alert": None,
            },
            # Scenario 2: Fully approved invoice awaiting payment
            {
                "invoice_number": "INV-2024-002",
                "vendor_code": "VND-LAB-02",
                "po_number": "PO-2024-003",
                "dept_code": "ECE",
                "invoice_date": today - timedelta(days=16),
                "due_date": today + timedelta(days=14),
                "subtotal": Decimal("12542.37"),
                "tax_amount": Decimal("2257.63"),
                "total_amount": Decimal("14800.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "MATCHED",
                "approval_status": "APPROVED",
                "payment_status": "SCHEDULED",
                "lines": [{"desc": "Digital Storage 4-Channel Oscilloscopes 200MHz", "qty": Decimal("4.00"), "unit_price": Decimal("3135.59"), "tax": Decimal("18.00"), "total": Decimal("14800.00")}],
                "approvals": [
                    {"approver": "nikola.tesla@university.edu", "level": 1, "status": "APPROVED", "comments": "Oscilloscopes calibrated and installed. Approved."},
                    {"approver": "robert.vance@university.edu", "level": 2, "status": "APPROVED", "comments": "Match successful, budget headroom adequate. Scheduled for disbursement."},
                ],
                "payment": {"ref": "PAY-2024-002", "date": today + timedelta(days=2), "amount": Decimal("14800.00"), "method": "WIRE", "status": "SCHEDULED"},
                "fraud_alert": None,
            },
            # Scenario 3: Normal invoice awaiting HOD approval
            {
                "invoice_number": "INV-2024-003",
                "vendor_code": "VND-PUB-03",
                "po_number": "PO-2024-004",
                "dept_code": "LIB",
                "invoice_date": today - timedelta(days=8),
                "due_date": today + timedelta(days=22),
                "subtotal": Decimal("12028.30"),
                "tax_amount": Decimal("721.70"),
                "total_amount": Decimal("12750.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "MATCHED",
                "approval_status": "PENDING",
                "payment_status": "UNPAID",
                "lines": [{"desc": "Advanced Deep Learning & Systems Textbooks (Vol 1-3)", "qty": Decimal("150.00"), "unit_price": Decimal("80.19"), "tax": Decimal("6.00"), "total": Decimal("12750.00")}],
                "approvals": [
                    {"approver": "sarah.jenkins@university.edu", "level": 1, "status": "PENDING", "comments": "Pending library director confirmation."},
                ],
                "payment": None,
                "fraud_alert": None,
            },
            # Scenario 4: Duplicate Invoice Attempt (flagged with high fraud risk)
            {
                "invoice_number": "INV-2024-001-DUP",
                "vendor_code": "VND-TECH-01",
                "po_number": "PO-2024-001",
                "dept_code": "CSE",
                "invoice_date": today - timedelta(days=5),
                "due_date": today + timedelta(days=25),
                "subtotal": Decimal("30000.00"),
                "tax_amount": Decimal("5400.00"),
                "total_amount": Decimal("35400.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "DUPLICATE",
                "approval_status": "REJECTED",
                "payment_status": "CANCELLED",
                "lines": [{"desc": "High-Performance AI Compute Workstations (RTX 4090) - Resubmission", "qty": Decimal("10.00"), "unit_price": Decimal("3000.00"), "tax": Decimal("18.00"), "total": Decimal("35400.00")}],
                "approvals": [
                    {"approver": "robert.vance@university.edu", "level": 1, "status": "REJECTED", "comments": "Rejected: Exact duplicate of paid invoice INV-2024-001."},
                ],
                "payment": None,
                "fraud_alert": {
                    "alert_type": "DUPLICATE_INVOICE",
                    "severity": "CRITICAL",
                    "description": "Critical Duplicate Alert: Vendor submitted invoice for identical PO-2024-001 and identical amount ($35,400.00) already settled in PAY-2024-001.",
                    "risk_score": Decimal("98.50"),
                    "status": "OPEN",
                },
            },
            # Scenario 5: Invoice exceeding PO amount (Overbilling anomaly)
            {
                "invoice_number": "INV-2024-004",
                "vendor_code": "VND-TECH-01",
                "po_number": "PO-2024-002",
                "dept_code": "CSE",
                "invoice_date": today - timedelta(days=12),
                "due_date": today + timedelta(days=18),
                "subtotal": Decimal("10847.46"),
                "tax_amount": Decimal("1952.54"),
                "total_amount": Decimal("12800.00"),  # PO was $9,600!
                "extraction_status": "EXTRACTED",
                "processing_status": "EXCEPTION",
                "approval_status": "IN_REVIEW",
                "payment_status": "UNPAID",
                "lines": [{"desc": "UltraSharp 27-inch 4K Developer Displays (Inflated Surcharge)", "qty": Decimal("24.00"), "unit_price": Decimal("451.98"), "tax": Decimal("18.00"), "total": Decimal("12800.00")}],
                "approvals": [
                    {"approver": "alan.turing@university.edu", "level": 1, "status": "PENDING", "comments": "Under review: Amount is $3,200 higher than approved PO-2024-002."},
                ],
                "payment": None,
                "fraud_alert": {
                    "alert_type": "OVERBILLING",
                    "severity": "HIGH",
                    "description": "Overbilling Detected: Invoiced total ($12,800.00) exceeds PO-2024-002 total ($9,600.00) by 33.3% ($3,200.00 variance).",
                    "risk_score": Decimal("86.00"),
                    "status": "UNDER_REVIEW",
                },
            },
            # Scenario 6: Invoice with quantity mismatch (invoiced > goods received)
            {
                "invoice_number": "INV-2024-005",
                "vendor_code": "VND-OFF-04",
                "po_number": "PO-2024-006",
                "dept_code": "ADMIN",
                "invoice_date": today - timedelta(days=6),
                "due_date": today + timedelta(days=24),
                "subtotal": Decimal("18983.05"),
                "tax_amount": Decimal("3416.95"),
                "total_amount": Decimal("22400.00"),  # Billed for 80, but only 60 accepted!
                "extraction_status": "EXTRACTED",
                "processing_status": "EXCEPTION",
                "approval_status": "IN_REVIEW",
                "payment_status": "UNPAID",
                "lines": [{"desc": "Ergonomic Lumbar Executive Task Chairs (Full PO Count)", "qty": Decimal("80.00"), "unit_price": Decimal("237.29"), "tax": Decimal("18.00"), "total": Decimal("22400.00")}],
                "approvals": [],
                "payment": None,
                "fraud_alert": {
                    "alert_type": "QUANTITY_MISMATCH",
                    "severity": "HIGH",
                    "description": "Quantity Mismatch: Vendor billed for 80 units ($22,400.00), but Goods Receipt GRN-2024-006 accepted only 60 units (20 units damaged/rejected).",
                    "risk_score": Decimal("79.00"),
                    "status": "OPEN",
                },
            },
            # Scenario 7: Invoice with missing goods receipt
            {
                "invoice_number": "INV-2024-006",
                "vendor_code": "VND-CHEM-07",
                "po_number": "PO-2024-009",
                "dept_code": "BIOTECH",
                "invoice_date": today - timedelta(days=4),
                "due_date": today + timedelta(days=26),
                "subtotal": Decimal("7368.42"),
                "tax_amount": Decimal("1031.58"),
                "total_amount": Decimal("8400.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "EXCEPTION",
                "approval_status": "PENDING",
                "payment_status": "UNPAID",
                "lines": [{"desc": "Molecular Biology PCR Reagents & Assay Buffers Batch", "qty": Decimal("20.00"), "unit_price": Decimal("368.42"), "tax": Decimal("14.00"), "total": Decimal("8400.00")}],
                "approvals": [],
                "payment": None,
                "fraud_alert": {
                    "alert_type": "UNRECOGNIZED_LINE_ITEM",
                    "severity": "MEDIUM",
                    "description": "Three-Way Match Failed: No Goods Receipt Note (GRN) found for PO-2024-009. Delivery pending confirmation.",
                    "risk_score": Decimal("62.50"),
                    "status": "OPEN",
                },
            },
            # Scenario 8: Invoice exceeding department budget
            {
                "invoice_number": "INV-2024-007",
                "vendor_code": "VND-NET-05",
                "po_number": "PO-2024-008",
                "dept_code": "CSE",
                "invoice_date": today - timedelta(days=3),
                "due_date": today + timedelta(days=27),
                "subtotal": Decimal("24491.53"),
                "tax_amount": Decimal("4408.47"),
                "total_amount": Decimal("28900.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "EXCEPTION",
                "approval_status": "IN_REVIEW",
                "payment_status": "UNPAID",
                "lines": [{"desc": "Enterprise 48-Port 10Gbps Managed SFP+ Switches", "qty": Decimal("4.00"), "unit_price": Decimal("6122.88"), "tax": Decimal("18.00"), "total": Decimal("28900.00")}],
                "approvals": [
                    {"approver": "alan.turing@university.edu", "level": 1, "status": "APPROVED", "comments": "Switches installed in CSE network core."},
                    {"approver": "sarah.jenkins@university.edu", "level": 2, "status": "PENDING", "comments": "Evaluating budget overrun exception against Q4 allocation."},
                ],
                "payment": None,
                "fraud_alert": {
                    "alert_type": "BUDGET_EXCEEDED",
                    "severity": "HIGH",
                    "description": "Budget Ceiling Exceeded: Invoiced amount of $28,900.00 exceeds remaining uncommitted budget allocation threshold for CSE.",
                    "risk_score": Decimal("74.00"),
                    "status": "UNDER_REVIEW",
                },
            },
            # Scenario 9: Invoice in review / routine multi-stage approval
            {
                "invoice_number": "INV-2024-008",
                "vendor_code": "VND-FAC-06",
                "po_number": "PO-2024-007",
                "dept_code": "ADMIN",
                "invoice_date": today - timedelta(days=2),
                "due_date": today + timedelta(days=28),
                "subtotal": Decimal("13983.05"),
                "tax_amount": Decimal("2516.95"),
                "total_amount": Decimal("16500.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "MATCHED",
                "approval_status": "IN_REVIEW",
                "payment_status": "UNPAID",
                "lines": [{"desc": "Annual Central HVAC Diagnostic & Air Filter Maintenance", "qty": Decimal("1.00"), "unit_price": Decimal("13983.05"), "tax": Decimal("18.00"), "total": Decimal("16500.00")}],
                "approvals": [
                    {"approver": "robert.vance@university.edu", "level": 1, "status": "APPROVED", "comments": "HVAC service logs verified with engineering office."},
                    {"approver": "sarah.jenkins@university.edu", "level": 2, "status": "PENDING", "comments": "Awaiting final administrative sign-off."},
                ],
                "payment": None,
                "fraud_alert": None,
            },
            # Scenario 10: Fully matched invoice, approved, ready for payment scheduling
            {
                "invoice_number": "INV-2024-009",
                "vendor_code": "VND-SOFT-08",
                "po_number": "PO-2024-010",
                "dept_code": "CSE",
                "invoice_date": today - timedelta(days=1),
                "due_date": today + timedelta(days=29),
                "subtotal": Decimal("12711.86"),
                "tax_amount": Decimal("2288.14"),
                "total_amount": Decimal("15000.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "MATCHED",
                "approval_status": "APPROVED",
                "payment_status": "UNPAID",
                "lines": [{"desc": "100-Seat Academic Simulation Software Enterprise License", "qty": Decimal("1.00"), "unit_price": Decimal("12711.86"), "tax": Decimal("18.00"), "total": Decimal("15000.00")}],
                "approvals": [
                    {"approver": "alan.turing@university.edu", "level": 1, "status": "APPROVED", "comments": "Site license active on CSE cloud cluster."},
                    {"approver": "sarah.jenkins@university.edu", "level": 2, "status": "APPROVED", "comments": "Approved. Batch into upcoming Friday disbursement."},
                ],
                "payment": None,
                "fraud_alert": None,
            },
            # Scenario 11: Newly extracted invoice, pending matching agent run
            {
                "invoice_number": "INV-2024-010",
                "vendor_code": "VND-LAB-02",
                "po_number": "PO-2024-005",
                "dept_code": "MECH",
                "invoice_date": today,
                "due_date": today + timedelta(days=30),
                "subtotal": Decimal("15423.73"),
                "tax_amount": Decimal("2776.27"),
                "total_amount": Decimal("18200.00"),
                "extraction_status": "EXTRACTED",
                "processing_status": "PROCESSING",
                "approval_status": "PENDING",
                "payment_status": "UNPAID",
                "lines": [{"desc": "CNC 5-Axis Milling Machine Laser Calibration Unit", "qty": Decimal("1.00"), "unit_price": Decimal("15423.73"), "tax": Decimal("18.00"), "total": Decimal("18200.00")}],
                "approvals": [],
                "payment": None,
                "fraud_alert": None,
            },
        ]

        invoices = {}
        for inv_dict in invoices_data:
            norm_num = normalize_invoice_number(inv_dict["invoice_number"])
            vendor_id = vendors[inv_dict["vendor_code"]].id
            existing = db.query(Invoice).filter_by(vendor_id=vendor_id, normalized_invoice_number=norm_num).first()
            if not existing:
                po = purchase_orders.get(inv_dict["po_number"]) if inv_dict["po_number"] else None
                existing = Invoice(
                    invoice_number=inv_dict["invoice_number"],
                    normalized_invoice_number=norm_num,
                    vendor_id=vendor_id,
                    purchase_order_id=po.id if po else None,
                    department_id=departments[inv_dict["dept_code"]].id,
                    invoice_date=inv_dict["invoice_date"],
                    due_date=inv_dict["due_date"],
                    subtotal=inv_dict["subtotal"],
                    tax_amount=inv_dict["tax_amount"],
                    total_amount=inv_dict["total_amount"],
                    currency="USD",
                    extraction_status=inv_dict["extraction_status"],
                    processing_status=inv_dict["processing_status"],
                    approval_status=inv_dict["approval_status"],
                    payment_status=inv_dict["payment_status"],
                    document_path=f"uploads/invoices/{inv_dict['invoice_number'].lower()}.pdf",
                    original_filename=f"{inv_dict['invoice_number']}.pdf",
                )
                db.add(existing)
                db.flush()

                # Add lines
                for idx, line_spec in enumerate(inv_dict["lines"], start=1):
                    inv_line = InvoiceLine(
                        invoice_id=existing.id,
                        line_number=idx,
                        description=line_spec["desc"],
                        quantity=line_spec["qty"],
                        unit_price=line_spec["unit_price"],
                        tax_rate=line_spec["tax"],
                        line_total=line_spec["total"],
                    )
                    db.add(inv_line)
                    db.flush()

                # Add approvals
                for app_spec in inv_dict.get("approvals", []):
                    approver_user = users[app_spec["approver"]]
                    decided = datetime.now(timezone.utc) if app_spec["status"] != "PENDING" else None
                    app_rec = Approval(
                        invoice_id=existing.id,
                        approver_id=approver_user.id,
                        approval_level=app_spec["level"],
                        status=app_spec["status"],
                        comments=app_spec["comments"],
                        decided_at=decided,
                    )
                    db.add(app_rec)
                    db.flush()

                # Add payment if present
                pay_spec = inv_dict.get("payment")
                if pay_spec:
                    pay_rec = Payment(
                        invoice_id=existing.id,
                        payment_reference=pay_spec["ref"],
                        scheduled_date=pay_spec["date"] if pay_spec["status"] == "SCHEDULED" else today - timedelta(days=7),
                        payment_date=pay_spec["date"] if pay_spec["status"] == "COMPLETED" else None,
                        amount=pay_spec["amount"],
                        status=pay_spec["status"],
                        payment_method=pay_spec["method"],
                        external_reference=f"MOCK-FEDWIRE-{pay_spec['ref']}",
                    )
                    db.add(pay_rec)
                    db.flush()

                # Add fraud alert if present
                fa_spec = inv_dict.get("fraud_alert")
                if fa_spec:
                    fa_rec = FraudAlert(
                        invoice_id=existing.id,
                        alert_type=fa_spec["alert_type"],
                        severity=fa_spec["severity"],
                        description=fa_spec["description"],
                        risk_score=fa_spec["risk_score"],
                        status=fa_spec["status"],
                    )
                    db.add(fa_rec)
                    db.flush()

                print(f"  + Added Invoice: {existing.invoice_number} ({existing.processing_status} / {existing.approval_status})")
            invoices[existing.invoice_number] = existing

        # -------------------------------------------------------------
        # 8. Audit Logs & Agent Execution Logs
        # -------------------------------------------------------------
        if db.query(AuditLog).count() == 0:
            audit_events = [
                {
                    "user_id": users["marcus.chen@university.edu"].id,
                    "action": "PURCHASE_ORDER_ISSUED",
                    "entity_type": "PURCHASE_ORDER",
                    "entity_id": str(purchase_orders["PO-2024-001"].id),
                    "old_values": None,
                    "new_values": {"po_number": "PO-2024-001", "vendor": "Apex Computing", "amount": 35400.00},
                    "ip_address": "192.168.10.15",
                },
                {
                    "user_id": users["marcus.chen@university.edu"].id,
                    "action": "GOODS_RECEIPT_LOGGED",
                    "entity_type": "GOODS_RECEIPT",
                    "entity_id": str(goods_receipts["GRN-2024-001"].id),
                    "old_values": None,
                    "new_values": {"grn_number": "GRN-2024-001", "po_number": "PO-2024-001", "accepted_qty": 10},
                    "ip_address": "192.168.10.15",
                },
                {
                    "user_id": None,
                    "action": "INVOICE_OCR_EXTRACTED",
                    "entity_type": "INVOICE",
                    "entity_id": str(invoices["INV-2024-001"].id),
                    "old_values": {"status": "RECEIVED"},
                    "new_values": {"status": "EXTRACTED", "total_amount": 35400.00, "confidence": 0.99},
                    "ip_address": "127.0.0.1",
                },
                {
                    "user_id": None,
                    "action": "THREE_WAY_MATCH_SUCCESS",
                    "entity_type": "INVOICE",
                    "entity_id": str(invoices["INV-2024-001"].id),
                    "old_values": {"processing_status": "PROCESSING"},
                    "new_values": {"processing_status": "MATCHED", "variance": 0.00},
                    "ip_address": "127.0.0.1",
                },
                {
                    "user_id": users["alan.turing@university.edu"].id,
                    "action": "INVOICE_STAGE1_APPROVED",
                    "entity_type": "INVOICE",
                    "entity_id": str(invoices["INV-2024-001"].id),
                    "old_values": {"approval_status": "PENDING"},
                    "new_values": {"approval_status": "IN_REVIEW", "approver": "Alan Turing"},
                    "ip_address": "192.168.20.44",
                },
                {
                    "user_id": users["sarah.jenkins@university.edu"].id,
                    "action": "INVOICE_FINAL_APPROVED",
                    "entity_type": "INVOICE",
                    "entity_id": str(invoices["INV-2024-001"].id),
                    "old_values": {"approval_status": "IN_REVIEW"},
                    "new_values": {"approval_status": "APPROVED", "approver": "Sarah Jenkins"},
                    "ip_address": "192.168.10.2",
                },
                {
                    "user_id": None,
                    "action": "FRAUD_ALERT_FLAGGED",
                    "entity_type": "FRAUD_ALERT",
                    "entity_id": "1",
                    "old_values": None,
                    "new_values": {"type": "DUPLICATE_INVOICE", "risk_score": 98.50, "invoice": "INV-2024-001-DUP"},
                    "ip_address": "127.0.0.1",
                },
                {
                    "user_id": users["robert.vance@university.edu"].id,
                    "action": "PAYMENT_SETTLED",
                    "entity_type": "PAYMENT",
                    "entity_id": "1",
                    "old_values": {"status": "SCHEDULED"},
                    "new_values": {"status": "COMPLETED", "reference": "PAY-2024-001", "amount": 35400.00},
                    "ip_address": "192.168.10.8",
                },
            ]
            for evt in audit_events:
                db.add(AuditLog(**evt))
            db.flush()
            print(f"  + Added {len(audit_events)} demonstration audit log entries.")

        if db.query(AgentExecutionLog).count() == 0:
            agent_runs = [
                {
                    "invoice_id": invoices["INV-2024-001"].id,
                    "agent_name": "IntakeAgent",
                    "execution_status": "COMPLETED",
                    "input_summary": "Extracted text and metadata from PDF invoice INV-2024-001",
                    "output_summary": "Extracted 1 line items, subtotal: $30000.00, tax: $5400.00, total: $35400.00",
                    "execution_duration": Decimal("1.2400"),
                },
                {
                    "invoice_id": invoices["INV-2024-001"].id,
                    "agent_name": "MatchingAgent",
                    "execution_status": "COMPLETED",
                    "input_summary": "Comparing INV-2024-001 against PO-2024-001 and GRN-2024-001",
                    "output_summary": "Perfect 3-way match: PO line count 1, GRN accepted qty 10.00, invoice qty 10.00. Zero price variance.",
                    "execution_duration": Decimal("0.8500"),
                },
                {
                    "invoice_id": invoices["INV-2024-001"].id,
                    "agent_name": "FraudAgent",
                    "execution_status": "COMPLETED",
                    "input_summary": "Heuristic fraud check for duplicate invoice number and bank route validation",
                    "output_summary": "Risk Score: 5.0 (LOW). No previous invoice matching fingerprint found.",
                    "execution_duration": Decimal("0.4200"),
                },
                {
                    "invoice_id": invoices["INV-2024-001-DUP"].id,
                    "agent_name": "FraudAgent",
                    "execution_status": "WARNING",
                    "input_summary": "Duplicate anomaly check on resubmitted invoice",
                    "output_summary": "High risk detected: Risk score 98.50. Exact amount and PO duplicate found.",
                    "execution_duration": Decimal("0.3800"),
                },
            ]
            for ar in agent_runs:
                db.add(AgentExecutionLog(**ar))
            db.flush()
            print(f"  + Added {len(agent_runs)} agent execution records.")

        db.commit()
        print("✅ Database seeding successfully completed!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during database seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

