#!/usr/bin/env python3
"""
JKLU AP Dataset Safe Production Importer
Safely imports synthetic JKLU dataset records into PostgreSQL database.

Safety Guarantees:
- Append-only: Never modifies, deletes, or resets existing records or sequences.
- Idempotent: Skips existing records by unique keys (vendor_code, po_number, grn_number, invoice_number, payment_reference).
- Strict Relational Integrity: Resolves and maps parent foreign keys.
- Atomic Transaction: Full rollback on any validation or constraint violation.
- No Fabricated Logs: Does not insert simulated AI execution logs or illustrative journal vouchers.
- Dry-Run by Default: Does not commit changes unless --execute is explicitly supplied.
"""

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_database_name
from app.models import (
    Approval,
    Budget,
    ChartOfAccount,
    Department,
    FraudAlert,
    GoodsReceipt,
    GoodsReceiptLine,
    Invoice,
    InvoiceLine,
    Payment,
    PurchaseOrder,
    PurchaseOrderLine,
    User,
    Vendor,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("jklu.importer")

DATASET_JSON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "jklu", "JKLU_AP_Dataset.json")
)

DEMO_DATABASE_NAME = "bahi_ai_demo"


def resolve_target_database(db: Optional[Session] = None) -> str:
    """
    Resolves the target database name from a SQLAlchemy session or connection engine.
    """
    if db is not None:
        try:
            return get_database_name(db)
        except Exception:
            pass
    return get_database_name()


def validate_target_database(db: Optional[Session] = None, dry_run: bool = True) -> str:
    """
    Validates that live import (--execute) is strictly restricted to 'bahi_ai_demo'.

    Safety Rules:
    - Dry-run validation is permitted on any database and performs zero writes.
    - Live import (--execute / dry_run=False) is ONLY allowed when the resolved
      database name is exactly 'bahi_ai_demo'.
    - No bypass flags (e.g. --allow-any-db) are supported or permitted.

    Raises:
        RuntimeError: If dry_run is False and the resolved database name is not 'bahi_ai_demo'.
    """
    target_db = resolve_target_database(db)

    if not dry_run:
        if target_db != DEMO_DATABASE_NAME:
            error_msg = (
                f"CRITICAL SAFETY VIOLATION: Live import (--execute) is strictly prohibited on database '{target_db}'. "
                f"Live execution is only permitted when connected to '{DEMO_DATABASE_NAME}'. "
                f"Operation aborted to protect database integrity."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

    return target_db


class JKLUDataSetImporter:
    def __init__(self, db: Session, dry_run: bool = True):
        self.db = db
        self.dry_run = dry_run
        # Strict safety guard: Validate target database immediately on instantiation
        self.target_db = validate_target_database(self.db, self.dry_run)
        self.stats: Dict[str, Dict[str, int]] = {
            "departments": {"matched": 0, "inserted": 0, "skipped": 0},
            "users": {"matched": 0, "inserted": 0, "skipped": 0},
            "vendors": {"matched": 0, "inserted": 0, "skipped": 0},
            "budgets": {"matched": 0, "inserted": 0, "skipped": 0},
            "purchase_orders": {"matched": 0, "inserted": 0, "skipped": 0},
            "po_lines": {"matched": 0, "inserted": 0, "skipped": 0},
            "goods_receipts": {"matched": 0, "inserted": 0, "skipped": 0},
            "grn_lines": {"matched": 0, "inserted": 0, "skipped": 0},
            "invoices": {"matched": 0, "inserted": 0, "skipped": 0},
            "invoice_lines": {"matched": 0, "inserted": 0, "skipped": 0},
            "approvals": {"matched": 0, "inserted": 0, "skipped": 0},
            "fraud_alerts": {"matched": 0, "inserted": 0, "skipped": 0},
            "payments": {"matched": 0, "inserted": 0, "skipped": 0},
        }
        # Mappings from dataset ID -> actual DB entity ID
        self.dept_map: Dict[int, int] = {}
        self.user_map: Dict[int, int] = {}
        self.vendor_map: Dict[int, int] = {}
        self.po_map: Dict[int, int] = {}
        self.pol_map: Dict[int, int] = {}
        self.grn_map: Dict[int, int] = {}
        self.inv_map: Dict[int, int] = {}
        self.duplicates_report: List[Dict[str, Any]] = []

    def load_dataset(self) -> Dict[str, Any]:
        if not os.path.exists(DATASET_JSON_PATH):
            raise FileNotFoundError(f"Dataset JSON not found at {DATASET_JSON_PATH}")
        with open(DATASET_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def resolve_departments(self, dataset_depts: List[Dict[str, Any]]):
        logger.info("Resolving university departments...")
        for d in dataset_depts:
            db_dept = self.db.query(Department).filter(Department.code == d["code"]).first()
            if db_dept:
                self.dept_map[d["id"]] = db_dept.id
                self.stats["departments"]["matched"] += 1
            else:
                if not self.dry_run:
                    new_dept = Department(
                        name=d["name"],
                        code=d["code"],
                        description=d.get("description"),
                        is_active=d.get("is_active", True),
                    )
                    self.db.add(new_dept)
                    self.db.flush()
                    self.dept_map[d["id"]] = new_dept.id
                self.stats["departments"]["inserted"] += 1

    def resolve_users(self, dataset_users: List[Dict[str, Any]]):
        logger.info("Resolving university users...")
        for u in dataset_users:
            db_user = self.db.query(User).filter(User.email == u["email"]).first()
            if db_user:
                self.user_map[u["id"]] = db_user.id
                self.stats["users"]["matched"] += 1
            else:
                if not self.dry_run:
                    # Provide default mock password hash for new user
                    new_user = User(
                        full_name=u["full_name"],
                        email=u["email"],
                        password_hash="$argon2id$v=19$m=65536,t=3,p=4$syntheticuserhash",
                        role=u["role"],
                        department_id=self.dept_map.get(u.get("department_id")),
                        is_active=u.get("is_active", True),
                    )
                    self.db.add(new_user)
                    self.db.flush()
                    self.user_map[u["id"]] = new_user.id
                self.stats["users"]["inserted"] += 1

    def resolve_vendors(self, dataset_vendors: List[Dict[str, Any]]):
        logger.info("Resolving vendors (matching existing + inserting new Rajasthan suppliers)...")
        for v in dataset_vendors:
            db_v = self.db.query(Vendor).filter(Vendor.vendor_code == v["vendor_code"]).first()
            if db_v:
                self.vendor_map[v["id"]] = db_v.id
                self.stats["vendors"]["matched"] += 1
            else:
                if not self.dry_run:
                    new_v = Vendor(
                        vendor_code=v["vendor_code"],
                        legal_name=v["legal_name"],
                        contact_person=v["contact_person"],
                        email=v["email"],
                        phone=v["phone"],
                        address=v["address"],
                        tax_identifier=v["tax_identifier"],
                        bank_account_last_four=v["bank_account_last_four"],
                        bank_name=v["bank_name"],
                        is_active=v.get("is_active", True),
                    )
                    self.db.add(new_v)
                    self.db.flush()
                    self.vendor_map[v["id"]] = new_v.id
                else:
                    self.vendor_map[v["id"]] = 9000 + v["id"]
                self.stats["vendors"]["inserted"] += 1

    def resolve_budgets(self, dataset_budgets: List[Dict[str, Any]]):
        logger.info("Verifying department budget allocations...")
        for b in dataset_budgets:
            actual_dept_id = self.dept_map.get(b["department_id"])
            if not actual_dept_id:
                continue
            db_b = (
                self.db.query(Budget)
                .filter(
                    Budget.department_id == actual_dept_id,
                    Budget.fiscal_year == b["fiscal_year"],
                )
                .first()
            )
            if db_b:
                self.stats["budgets"]["matched"] += 1
            else:
                if not self.dry_run:
                    new_b = Budget(
                        department_id=actual_dept_id,
                        fiscal_year=b["fiscal_year"],
                        allocated_amount=Decimal(str(b["allocated_amount"])),
                        committed_amount=Decimal(str(b["committed_amount"])),
                        spent_amount=Decimal(str(b["spent_amount"])),
                        available_amount=Decimal(str(b["available_amount"])),
                    )
                    self.db.add(new_b)
                    self.db.flush()
                self.stats["budgets"]["inserted"] += 1

    def import_purchase_orders(
        self, dataset_pos: List[Dict[str, Any]], dataset_polines: List[Dict[str, Any]]
    ):
        logger.info("Processing Purchase Orders and Line Items...")
        lines_by_po = {}
        for l in dataset_polines:
            lines_by_po.setdefault(l["purchase_order_id"], []).append(l)

        seen_pos: Dict[str, Tuple[int, Dict[int, int]]] = {}

        for p in dataset_pos:
            po_num = p["po_number"]
            if po_num in seen_pos:
                prev_id, prev_lines = seen_pos[po_num]
                self.po_map[p["id"]] = prev_id
                self.stats["purchase_orders"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "PurchaseOrder",
                    "identifier": po_num,
                    "action": "SKIPPED_DUPLICATE_BATCH",
                    "existing_id": prev_id,
                })
                for d_l in lines_by_po.get(p["id"], []):
                    if d_l["line_number"] in prev_lines:
                        self.pol_map[d_l["id"]] = prev_lines[d_l["line_number"]]
                continue

            existing_po = self.db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_num).first()
            if existing_po:
                self.po_map[p["id"]] = existing_po.id
                self.stats["purchase_orders"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "PurchaseOrder",
                    "identifier": po_num,
                    "action": "SKIPPED_EXISTING",
                    "existing_id": existing_po.id,
                })
                # map existing lines
                existing_lines = {}
                for db_l in existing_po.lines:
                    existing_lines[db_l.line_number] = db_l.id
                    for d_l in lines_by_po.get(p["id"], []):
                        if db_l.line_number == d_l["line_number"]:
                            self.pol_map[d_l["id"]] = db_l.id
                seen_pos[po_num] = (existing_po.id, existing_lines)
                continue

            actual_v_id = self.vendor_map.get(p["vendor_id"])
            actual_d_id = self.dept_map.get(p["department_id"])
            actual_u_id = self.user_map.get(p.get("created_by", 3), 3)

            if not self.dry_run:
                new_po = PurchaseOrder(
                    po_number=p["po_number"],
                    vendor_id=actual_v_id,
                    department_id=actual_d_id,
                    issue_date=date.fromisoformat(p["issue_date"]),
                    expected_delivery_date=date.fromisoformat(p["expected_delivery_date"]) if p.get("expected_delivery_date") else None,
                    total_amount=Decimal(str(p["total_amount"])),
                    tax_amount=Decimal(str(p["tax_amount"])),
                    status=p["status"],
                    created_by=actual_u_id,
                )
                self.db.add(new_po)
                self.db.flush()
                self.po_map[p["id"]] = new_po.id

                created_lines = {}
                for l in lines_by_po.get(p["id"], []):
                    new_l = PurchaseOrderLine(
                        purchase_order_id=new_po.id,
                        line_number=l["line_number"],
                        item_description=l["item_description"],
                        quantity=Decimal(str(l["quantity"])),
                        unit_price=Decimal(str(l["unit_price"])),
                        tax_rate=Decimal(str(l["tax_rate"])),
                        total_amount=Decimal(str(l["total_amount"])),
                    )
                    self.db.add(new_l)
                    self.db.flush()
                    self.pol_map[l["id"]] = new_l.id
                    created_lines[l["line_number"]] = new_l.id
                    self.stats["po_lines"]["inserted"] += 1
                seen_pos[po_num] = (new_po.id, created_lines)
            else:
                mock_po_id = 8000 + p["id"]
                self.po_map[p["id"]] = mock_po_id
                mock_lines = {}
                for l in lines_by_po.get(p["id"], []):
                    mock_lid = 8500 + l["id"]
                    self.pol_map[l["id"]] = mock_lid
                    mock_lines[l["line_number"]] = mock_lid
                    self.stats["po_lines"]["inserted"] += 1
                seen_pos[po_num] = (mock_po_id, mock_lines)

            self.stats["purchase_orders"]["inserted"] += 1

    def import_goods_receipts(
        self, dataset_grns: List[Dict[str, Any]], dataset_grnlines: List[Dict[str, Any]]
    ):
        logger.info("Processing Goods Receipts (GRN) and lines...")
        lines_by_grn = {}
        for l in dataset_grnlines:
            lines_by_grn.setdefault(l["goods_receipt_id"], []).append(l)

        seen_grns: Dict[str, int] = {}

        for g in dataset_grns:
            grn_num = g["grn_number"]
            if grn_num in seen_grns:
                prev_id = seen_grns[grn_num]
                self.grn_map[g["id"]] = prev_id
                self.stats["goods_receipts"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "GoodsReceipt",
                    "identifier": grn_num,
                    "action": "SKIPPED_DUPLICATE_BATCH",
                    "existing_id": prev_id,
                })
                continue

            existing_grn = self.db.query(GoodsReceipt).filter(GoodsReceipt.grn_number == grn_num).first()
            if existing_grn:
                self.grn_map[g["id"]] = existing_grn.id
                self.stats["goods_receipts"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "GoodsReceipt",
                    "identifier": grn_num,
                    "action": "SKIPPED_EXISTING",
                    "existing_id": existing_grn.id,
                })
                seen_grns[grn_num] = existing_grn.id
                continue

            actual_po_id = self.po_map.get(g["purchase_order_id"])
            actual_u_id = self.user_map.get(g.get("received_by", 3), 3)

            if not self.dry_run:
                new_grn = GoodsReceipt(
                    grn_number=grn_num,
                    purchase_order_id=actual_po_id,
                    received_by=actual_u_id,
                    received_date=date.fromisoformat(g["received_date"]),
                    status=g["status"],
                    notes=g.get("notes"),
                )
                self.db.add(new_grn)
                self.db.flush()
                self.grn_map[g["id"]] = new_grn.id
                seen_grns[grn_num] = new_grn.id

                for l in lines_by_grn.get(g["id"], []):
                    actual_pol_id = self.pol_map.get(l["purchase_order_line_id"])
                    new_gl = GoodsReceiptLine(
                        goods_receipt_id=new_grn.id,
                        purchase_order_line_id=actual_pol_id,
                        quantity_ordered=Decimal(str(l["quantity_ordered"])),
                        quantity_received=Decimal(str(l["quantity_received"])),
                        quantity_accepted=Decimal(str(l["quantity_accepted"])),
                        quantity_rejected=Decimal(str(l["quantity_rejected"])),
                        notes=l.get("notes"),
                    )
                    self.db.add(new_gl)
                    self.stats["grn_lines"]["inserted"] += 1
                self.db.flush()
            else:
                mock_grn_id = 7000 + g["id"]
                self.grn_map[g["id"]] = mock_grn_id
                seen_grns[grn_num] = mock_grn_id
                for l in lines_by_grn.get(g["id"], []):
                    self.stats["grn_lines"]["inserted"] += 1

            self.stats["goods_receipts"]["inserted"] += 1

    def import_invoices(
        self, dataset_invoices: List[Dict[str, Any]], dataset_invlines: List[Dict[str, Any]]
    ):
        logger.info("Processing Invoices and Itemized Lines...")
        lines_by_inv = {}
        for l in dataset_invlines:
            lines_by_inv.setdefault(l["invoice_id"], []).append(l)

        for inv in dataset_invoices:
            # Check unique normalized invoice number collision or hash
            existing_inv = (
                self.db.query(Invoice)
                .filter(Invoice.normalized_invoice_number == inv["normalized_invoice_number"])
                .first()
            )
            if existing_inv:
                self.inv_map[inv["id"]] = existing_inv.id
                self.stats["invoices"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "Invoice",
                    "identifier": inv["invoice_number"],
                    "action": "SKIPPED_EXISTING",
                    "existing_id": existing_inv.id,
                })
                continue

            actual_v_id = self.vendor_map.get(inv.get("vendor_id")) if inv.get("vendor_id") else None
            actual_po_id = self.po_map.get(inv.get("purchase_order_id")) if inv.get("purchase_order_id") else None
            actual_d_id = self.dept_map.get(inv.get("department_id")) if inv.get("department_id") else None

            if not self.dry_run:
                new_inv = Invoice(
                    invoice_number=inv["invoice_number"],
                    normalized_invoice_number=inv["normalized_invoice_number"],
                    vendor_id=actual_v_id,
                    purchase_order_id=actual_po_id,
                    department_id=actual_d_id,
                    invoice_date=date.fromisoformat(inv["invoice_date"]) if inv.get("invoice_date") else None,
                    due_date=date.fromisoformat(inv["due_date"]) if inv.get("due_date") else None,
                    subtotal=Decimal(str(inv["subtotal"])) if inv.get("subtotal") is not None else None,
                    tax_amount=Decimal(str(inv["tax_amount"])),
                    total_amount=Decimal(str(inv["total_amount"])),
                    currency=inv.get("currency", "INR"),
                    description=inv.get("description"),
                    tax_identifier=inv.get("tax_identifier"),
                    document_path=inv.get("document_path"),
                    original_filename=inv.get("original_filename"),
                    file_hash=inv.get("file_hash"),
                    file_size=inv.get("file_size"),
                    mime_type=inv.get("mime_type"),
                    extraction_status=inv.get("extraction_status", "EXTRACTED"),
                    processing_status=inv.get("processing_status", "MATCHED"),
                    approval_status=inv.get("approval_status", "PENDING"),
                    payment_status=inv.get("payment_status", "UNPAID"),
                    confidence_score=Decimal(str(inv.get("confidence_score", 95.0))),
                    extraction_metadata=inv.get("extraction_metadata"),
                )
                self.db.add(new_inv)
                self.db.flush()
                self.inv_map[inv["id"]] = new_inv.id

                for l in lines_by_inv.get(inv["id"], []):
                    new_il = InvoiceLine(
                        invoice_id=new_inv.id,
                        line_number=l["line_number"],
                        description=l["description"],
                        quantity=Decimal(str(l["quantity"])),
                        unit_price=Decimal(str(l["unit_price"])),
                        tax_rate=Decimal(str(l["tax_rate"])),
                        line_total=Decimal(str(l["line_total"])),
                    )
                    self.db.add(new_il)
                    self.stats["invoice_lines"]["inserted"] += 1
                self.db.flush()
            else:
                self.inv_map[inv["id"]] = 6000 + inv["id"]
                for l in lines_by_inv.get(inv["id"], []):
                    self.stats["invoice_lines"]["inserted"] += 1

            self.stats["invoices"]["inserted"] += 1

    def import_approvals(self, dataset_approvals: List[Dict[str, Any]]):
        logger.info("Processing Approvals...")
        for a in dataset_approvals:
            actual_inv_id = self.inv_map.get(a["invoice_id"])
            if not actual_inv_id:
                continue
            actual_user_id = self.user_map.get(a["approver_id"], 1)

            # Check if approval step already exists
            existing_app = (
                self.db.query(Approval)
                .filter(
                    Approval.invoice_id == actual_inv_id,
                    Approval.approval_level == a["approval_level"],
                )
                .first()
            )
            if existing_app:
                self.stats["approvals"]["skipped"] += 1
                continue

            if not self.dry_run:
                decided = datetime.fromisoformat(a["decided_at"]) if a.get("decided_at") else None
                new_app = Approval(
                    invoice_id=actual_inv_id,
                    approver_id=actual_user_id,
                    approval_level=a["approval_level"],
                    status=a["status"],
                    comments=a.get("comments"),
                    decided_at=decided,
                )
                self.db.add(new_app)
                self.db.flush()
            self.stats["approvals"]["inserted"] += 1

    def import_fraud_alerts(self, dataset_fraud: List[Dict[str, Any]]):
        logger.info("Processing Fraud Alerts...")
        for f in dataset_fraud:
            actual_inv_id = self.inv_map.get(f["invoice_id"])
            if not actual_inv_id:
                continue

            existing_alert = (
                self.db.query(FraudAlert)
                .filter(
                    FraudAlert.invoice_id == actual_inv_id,
                    FraudAlert.alert_type == f["alert_type"],
                )
                .first()
            )
            if existing_alert:
                self.stats["fraud_alerts"]["skipped"] += 1
                continue

            if not self.dry_run:
                resolved = datetime.fromisoformat(f["resolved_at"]) if f.get("resolved_at") else None
                new_fa = FraudAlert(
                    invoice_id=actual_inv_id,
                    alert_type=f["alert_type"],
                    severity=f["severity"],
                    description=f["description"],
                    risk_score=Decimal(str(f["risk_score"])),
                    status=f["status"],
                    resolved_by=self.user_map.get(f.get("resolved_by")) if f.get("resolved_by") else None,
                    resolved_at=resolved,
                )
                self.db.add(new_fa)
                self.db.flush()
            self.stats["fraud_alerts"]["inserted"] += 1

    def import_payments(self, dataset_payments: List[Dict[str, Any]]):
        logger.info("Processing Payment Records...")
        for p in dataset_payments:
            actual_inv_id = self.inv_map.get(p["invoice_id"])
            if not actual_inv_id:
                continue

            existing_pay = (
                self.db.query(Payment)
                .filter(Payment.payment_reference == p["payment_reference"])
                .first()
            )
            if existing_pay:
                self.stats["payments"]["skipped"] += 1
                self.duplicates_report.append({
                    "entity": "Payment",
                    "identifier": p["payment_reference"],
                    "action": "SKIPPED_EXISTING",
                    "existing_id": existing_pay.id,
                })
                continue

            if not self.dry_run:
                p_date = date.fromisoformat(p["payment_date"]) if p.get("payment_date") else None
                new_pay = Payment(
                    invoice_id=actual_inv_id,
                    payment_reference=p["payment_reference"],
                    scheduled_date=date.fromisoformat(p["scheduled_date"]),
                    payment_date=p_date,
                    amount=Decimal(str(p["amount"])),
                    status=p["status"],
                    payment_method=p["payment_method"],
                    external_reference=p.get("external_reference"),
                )
                self.db.add(new_pay)
                self.db.flush()
            self.stats["payments"]["inserted"] += 1

    def run(self) -> Dict[str, Any]:
        # Enforce strict safety guard prior to any DB operation or dataset loading
        self.target_db = validate_target_database(self.db, self.dry_run)

        dataset = self.load_dataset()
        mode_str = "DRY-RUN (Simulated Validation Only - ZERO DB Writes)" if self.dry_run else "LIVE IMPORT (Atomic DB Commit)"
        logger.info(f"Target Database: '{self.target_db}'")
        logger.info(f"=== Starting JKLU Dataset Import: {mode_str} on '{self.target_db}' ===")

        try:
            self.resolve_departments(dataset.get("departments", []))
            self.resolve_users(dataset.get("users", []))
            self.resolve_vendors(dataset.get("vendors", []))
            self.resolve_budgets(dataset.get("budgets", []))
            self.import_purchase_orders(
                dataset.get("purchase_orders", []), dataset.get("purchase_order_lines", [])
            )
            self.import_goods_receipts(
                dataset.get("goods_receipts", []), dataset.get("goods_receipt_lines", [])
            )
            self.import_invoices(
                dataset.get("invoices", []), dataset.get("invoice_lines", [])
            )
            self.import_approvals(dataset.get("approvals", []))
            self.import_fraud_alerts(dataset.get("fraud_alerts", []))
            self.import_payments(dataset.get("payments", []))

            if self.dry_run:
                self.db.rollback()
                logger.info("Dry-run complete. Safe rollback performed.")
            else:
                self.db.commit()
                logger.info("Live import successful. Changes committed to database.")

            return {
                "dry_run": self.dry_run,
                "target_db": self.target_db,
                "stats": self.stats,
                "duplicates": self.duplicates_report,
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Import failed with error: {e}. Executed full rollback.")
            raise


def print_summary(result: Dict[str, Any]):
    stats = result["stats"]
    is_dry = result["dry_run"]
    target_db = result.get("target_db", "unknown")

    print("\n" + "=" * 65)
    print(f"  JKLU DATASET IMPORT SUMMARY ({'DRY-RUN MODE' if is_dry else 'LIVE EXECUTION'})")
    print(f"  Target Database: {target_db}")
    print("=" * 65)
    print(f" {'Entity Table':24} | {'Matched Existing':16} | {'New Records':12} | {'Skipped':8}")
    print("-" * 65)
    for k, v in stats.items():
        print(f" {k:24} | {v['matched']:16} | {v['inserted']:12} | {v['skipped']:8}")
    print("-" * 65)

    dups = result["duplicates"]
    if dups:
        print(f"\nDuplicate Detections / Collisions Handled: {len(dups)}")
        for d in dups[:10]:
            print(f"  - {d['entity']:16} [{d['identifier']}]: {d['action']}")
    else:
        print("\nNo collisions with existing DB records. Clean append-only import verified.")

    if is_dry:
        print(f"\n[NOTE] Dry-run completed against '{target_db}' with ZERO changes to the database.")
        print("To perform live import with atomic transaction, ensure connected to 'bahi_ai_demo' and execute:")
        print("  DATABASE_URL=postgresql://.../bahi_ai_demo python backend/app/scripts/import_jklu_dataset.py --execute\n")
    else:
        print(f"\n[SUCCESS] Live import completed on '{target_db}'. All new records safely committed to database.\n")


def main():
    parser = argparse.ArgumentParser(description="JKLU AP Dataset Safe Importer")
    parser.add_argument("--execute", action="store_true", help="Execute live import (commits changes to DB, strictly bahi_ai_demo only)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run validation in dry-run mode without DB commit (default)")
    args = parser.parse_args()

    # Dry-run is default unless --execute is explicitly supplied
    dry_run = not args.execute

    db = SessionLocal()
    try:
        # Pre-execution check prior to instantiating importer or loading data
        target_db = validate_target_database(db, dry_run=dry_run)
        if dry_run:
            print(f"\n[SAFETY NOTICE] Running in DRY-RUN mode against target database: '{target_db}' (Zero writes guaranteed)")
        else:
            print(f"\n[SAFETY NOTICE] Running in LIVE EXECUTION mode against verified target database: '{target_db}'")

        importer = JKLUDataSetImporter(db, dry_run=dry_run)
        result = importer.run()
        print_summary(result)
    except Exception as e:
        logger.error(f"Import process terminated: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

