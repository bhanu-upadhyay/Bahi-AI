from decimal import Decimal
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.schemas.agent import LineItemMatch, ThreeWayMatchingResult

logger = logging.getLogger("bahi_ai.agents.matching")


class ThreeWayMatchingAgent:
    """Agent 3 — Three-Way Matching Agent
    Cross-verifies Invoice lines and totals against authorized Purchase Orders (PO)
    and verified warehouse Goods Receipt Notes (GRN).
    Detects price variance, quantity overbilling, missing receipts, and partial deliveries.
    """

    def __init__(
        self,
        name: str = "ThreeWayMatchingAgent",
        price_tolerance_pct: Decimal = Decimal("0.00"),
        amount_tolerance_val: Decimal = Decimal("1.00"),
    ):
        self.name = name
        self.price_tolerance_pct = price_tolerance_pct
        self.amount_tolerance_val = amount_tolerance_val

    def execute(self, invoice: Invoice, db: Session) -> ThreeWayMatchingResult:
        logger.info(f"[{self.name}] Running 3-way match for Invoice #{invoice.invoice_number}")

        discrepancies: List[str] = []
        line_matches: List[LineItemMatch] = []
        grn_numbers: List[str] = []

        # 1. Check for linked Purchase Order
        po: Optional[PurchaseOrder] = None
        if invoice.purchase_order_id:
            po = (
                db.query(PurchaseOrder)
                .options(
                    joinedload(PurchaseOrder.lines),
                    joinedload(PurchaseOrder.goods_receipts).joinedload(GoodsReceipt.lines),
                )
                .filter(PurchaseOrder.id == invoice.purchase_order_id)
                .first()
            )

        # Fallback: search by PO number in extraction metadata if not explicitly linked
        if not po:
            po_num_extracted = (invoice.extraction_metadata or {}).get("purchase_order_number")
            if po_num_extracted:
                po = (
                    db.query(PurchaseOrder)
                    .options(
                        joinedload(PurchaseOrder.lines),
                        joinedload(PurchaseOrder.goods_receipts).joinedload(GoodsReceipt.lines),
                    )
                    .filter(PurchaseOrder.po_number.ilike(po_num_extracted.strip()))
                    .first()
                )

        # Case: Direct Spend (No PO)
        if not po:
            return ThreeWayMatchingResult(
                match_status="NO_PO",
                po_number=None,
                po_total=None,
                invoice_total=invoice.total_amount,
                total_variance=Decimal("0.00"),
                grn_numbers=[],
                line_matches=[],
                discrepancies=["Invoice is direct spend and does not reference an authorized university Purchase Order."],
                summary="Non-PO Direct Spend: Manual departmental budget check required.",
            )

        # 2. Verify Vendor & Department Consistency with PO
        if invoice.vendor_id and po.vendor_id != invoice.vendor_id:
            discrepancies.append(
                f"Vendor mismatch: PO #{po.po_number} is assigned to Vendor ID {po.vendor_id}, but invoice is billed to Vendor ID {invoice.vendor_id}."
            )

        if invoice.department_id and po.department_id != invoice.department_id:
            discrepancies.append(
                f"Department mismatch: PO #{po.po_number} belongs to Department ID {po.department_id}, but invoice is charged to Department ID {invoice.department_id}."
            )

        # 3. Retrieve Goods Receipt Notes (GRN)
        grns: List[GoodsReceipt] = po.goods_receipts or []
        grn_numbers = [g.grn_number for g in grns]

        # Case: PO exists but no GRN recorded
        if not grns:
            return ThreeWayMatchingResult(
                match_status="NO_GRN",
                po_number=po.po_number,
                po_total=po.total_amount,
                invoice_total=invoice.total_amount,
                total_variance=abs((invoice.total_amount or Decimal("0.00")) - po.total_amount),
                grn_numbers=[],
                line_matches=[],
                discrepancies=[f"Purchase Order #{po.po_number} has no Goods Receipt Notes (GRN) on record. Goods/services not yet received."],
                summary=f"Three-way match blocked: PO #{po.po_number} has zero confirmed deliveries in warehouse registry.",
            )

        # 4. Map GRN accepted quantities by PO Line ID
        grn_accepted_by_po_line: Dict[int, Decimal] = {}
        grn_received_by_po_line: Dict[int, Decimal] = {}
        for grn in grns:
            for grn_line in grn.lines:
                pid = grn_line.purchase_order_line_id
                grn_accepted_by_po_line[pid] = grn_accepted_by_po_line.get(pid, Decimal("0.00")) + grn_line.quantity_accepted
                grn_received_by_po_line[pid] = grn_received_by_po_line.get(pid, Decimal("0.00")) + grn_line.quantity_received

        # 5. Line-by-Line Matching (or Overall if invoice lines are not itemized)
        has_price_variance = False
        has_quantity_variance = False
        is_partial = False

        po_lines = {l.line_number: l for l in po.lines}
        invoice_lines = invoice.lines or []

        if invoice_lines:
            for inv_line in invoice_lines:
                po_l = po_lines.get(inv_line.line_number)
                if not po_l and len(po.lines) == 1:
                    po_l = po.lines[0]

                if po_l:
                    accepted_qty = grn_accepted_by_po_line.get(po_l.id, Decimal("0.00"))
                    p_var = inv_line.unit_price - po_l.unit_price
                    q_var = inv_line.quantity - accepted_qty

                    line_status = "MATCHED"
                    if p_var > Decimal("0.00"):
                        has_price_variance = True
                        line_status = "PRICE_VARIANCE"
                        discrepancies.append(
                            f"Line {inv_line.line_number} ('{inv_line.description}'): Unit price {inv_line.unit_price} exceeds PO price {po_l.unit_price} by {p_var}."
                        )
                    if q_var > Decimal("0.00"):
                        has_quantity_variance = True
                        line_status = "QUANTITY_VARIANCE"
                        discrepancies.append(
                            f"Line {inv_line.line_number} ('{inv_line.description}'): Invoiced quantity {inv_line.quantity} exceeds GRN accepted quantity {accepted_qty}."
                        )
                    elif accepted_qty < po_l.quantity:
                        is_partial = True

                    line_matches.append(
                        LineItemMatch(
                            line_number=inv_line.line_number,
                            description=inv_line.description,
                            po_quantity=po_l.quantity,
                            grn_accepted_quantity=accepted_qty,
                            invoice_quantity=inv_line.quantity,
                            po_unit_price=po_l.unit_price,
                            invoice_unit_price=inv_line.unit_price,
                            price_variance=p_var,
                            quantity_variance=q_var,
                            status=line_status,
                        )
                    )
                else:
                    discrepancies.append(f"Invoice line {inv_line.line_number} ('{inv_line.description}') not found on PO #{po.po_number}.")
                    line_matches.append(
                        LineItemMatch(
                            line_number=inv_line.line_number,
                            description=inv_line.description,
                            invoice_quantity=inv_line.quantity,
                            invoice_unit_price=inv_line.unit_price,
                            status="UNMATCHED",
                        )
                    )
        else:
            # Invoice has no itemized lines in DB, check overall total
            inv_tot = invoice.total_amount or Decimal("0.00")
            diff_tot = inv_tot - po.total_amount
            if diff_tot > self.amount_tolerance_val:
                has_price_variance = True
                discrepancies.append(
                    f"Invoice total ({inv_tot}) exceeds PO #{po.po_number} total ({po.total_amount}) by {diff_tot}."
                )

        # 6. Overall Status Determination
        inv_tot = invoice.total_amount or Decimal("0.00")
        total_variance = abs(inv_tot - po.total_amount)

        if has_quantity_variance:
            match_status = "QUANTITY_VARIANCE"
            summary = f"Match Failed: Invoiced quantities exceed warehouse accepted receipts on GRNs: {', '.join(grn_numbers)}."
        elif has_price_variance:
            match_status = "PRICE_VARIANCE"
            summary = f"Match Failed: Invoiced price exceeds authorized rate on PO #{po.po_number}."
        elif discrepancies:
            match_status = "DISCREPANCY"
            summary = f"Match Discrepancy: {'; '.join(discrepancies)}."
        elif is_partial:
            match_status = "PARTIAL_MATCH"
            summary = f"Partial Delivery Match: Invoiced quantities match partial delivery accepted on GRNs: {', '.join(grn_numbers)}."
        else:
            match_status = "FULL_MATCH"
            summary = f"Three-way match successful! Invoice #{invoice.invoice_number} perfectly reconciles with PO #{po.po_number} and GRNs ({', '.join(grn_numbers)})."

        return ThreeWayMatchingResult(
            match_status=match_status,
            po_number=po.po_number,
            po_total=po.total_amount,
            invoice_total=inv_tot,
            total_variance=total_variance,
            grn_numbers=grn_numbers,
            line_matches=line_matches,
            discrepancies=discrepancies,
            summary=summary,
        )
