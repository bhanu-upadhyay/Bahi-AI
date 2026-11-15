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
                if po:
                    invoice.purchase_order_id = po.id
                    if not invoice.vendor_id and po.vendor_id:
                        invoice.vendor_id = po.vendor_id
                    if not invoice.department_id and po.department_id:
                        invoice.department_id = po.department_id

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
        grns: List[GoodsReceipt] = list(po.goods_receipts or [])
        grn_num_extracted = (invoice.extraction_metadata or {}).get("grn_number")
        if not grns and grn_num_extracted:
            grn_match = (
                db.query(GoodsReceipt)
                .options(joinedload(GoodsReceipt.lines))
                .filter(GoodsReceipt.grn_number.ilike(grn_num_extracted.strip()))
                .first()
            )
            if grn_match:
                grns = [grn_match]

        grn_numbers = [g.grn_number for g in grns]

        # Case: PO exists but no GRN recorded
        if not grns:
            inv_tot = invoice.total_amount if invoice.total_amount is not None else Decimal("0.00")
            return ThreeWayMatchingResult(
                match_status="NO_GRN",
                po_number=po.po_number,
                po_total=po.total_amount,
                invoice_total=inv_tot,
                total_variance=inv_tot,
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
                grn_accepted_by_po_line[pid] = grn_accepted_by_po_line.get(pid, Decimal("0.00")) + Decimal(str(grn_line.quantity_accepted or 0))
                grn_received_by_po_line[pid] = grn_received_by_po_line.get(pid, Decimal("0.00")) + Decimal(str(grn_line.quantity_received or 0))

        # 5. Line-by-Line Matching (or Overall if invoice lines are not itemized)
        has_price_variance = False
        has_quantity_variance = False
        has_unmatched_lines = False
        is_partial = False
        total_monetary_variance = Decimal("0.00")

        po_lines_by_num = {l.line_number: l for l in po.lines}
        po_lines_by_desc = {l.item_description.strip().lower(): l for l in po.lines if l.item_description}
        invoice_lines = invoice.lines or []

        if invoice_lines:
            for inv_line in invoice_lines:
                po_l = po_lines_by_num.get(inv_line.line_number)
                if not po_l and inv_line.description:
                    po_l = po_lines_by_desc.get(inv_line.description.strip().lower())
                if not po_l and len(po.lines) == 1:
                    po_l = po.lines[0]

                inv_qty = Decimal(str(inv_line.quantity if inv_line.quantity is not None else 0))
                inv_price = Decimal(str(inv_line.unit_price if inv_line.unit_price is not None else 0))
                inv_tax_rate = Decimal(str(inv_line.tax_rate if inv_line.tax_rate is not None else 0)) / Decimal("100")
                inv_line_subtotal = (inv_qty * inv_price).quantize(Decimal("0.01"))

                if po_l:
                    po_qty = Decimal(str(po_l.quantity if po_l.quantity is not None else 0))
                    po_price = Decimal(str(po_l.unit_price if po_l.unit_price is not None else 0))
                    accepted_qty = grn_accepted_by_po_line.get(po_l.id, Decimal("0.00"))

                    p_var = (inv_price - po_price).quantize(Decimal("0.01"))
                    q_var = (inv_qty - accepted_qty).quantize(Decimal("0.01"))

                    line_status = "MATCHED"
                    if p_var > Decimal("0.00"):
                        has_price_variance = True
                        line_status = "PRICE_VARIANCE"
                        discrepancies.append(
                            f"Line {inv_line.line_number} ('{inv_line.description}'): Unit price {inv_price} exceeds authorized PO rate {po_price} by {p_var}."
                        )
                    if q_var > Decimal("0.00"):
                        has_quantity_variance = True
                        line_status = "QUANTITY_VARIANCE" if line_status == "MATCHED" else "PRICE_AND_QUANTITY_VARIANCE"
                        discrepancies.append(
                            f"Line {inv_line.line_number} ('{inv_line.description}'): Invoiced quantity {inv_qty} exceeds warehouse accepted receipt {accepted_qty} by {q_var}."
                        )
                    elif accepted_qty < po_qty or inv_qty < po_qty:
                        is_partial = True

                    # Monetary discrepancy calculation:
                    # Compare invoiced line subtotal against authorized subtotal for accepted quantity
                    auth_qty = max(Decimal("0.00"), min(inv_qty, accepted_qty))
                    authorized_subtotal = (auth_qty * po_price).quantize(Decimal("0.01"))
                    line_net_discrepancy = max(Decimal("0.00"), inv_line_subtotal - authorized_subtotal)
                    line_tax_discrepancy = (line_net_discrepancy * inv_tax_rate).quantize(Decimal("0.01"))
                    line_total_discrepancy = line_net_discrepancy + line_tax_discrepancy
                    total_monetary_variance += line_total_discrepancy

                    line_matches.append(
                        LineItemMatch(
                            line_number=inv_line.line_number,
                            description=inv_line.description,
                            po_quantity=po_qty,
                            grn_accepted_quantity=accepted_qty,
                            invoice_quantity=inv_qty,
                            po_unit_price=po_price,
                            invoice_unit_price=inv_price,
                            price_variance=p_var,
                            quantity_variance=q_var,
                            status=line_status,
                        )
                    )
                else:
                    has_unmatched_lines = True
                    discrepancies.append(f"Invoice line {inv_line.line_number} ('{inv_line.description}') not found on PO #{po.po_number}.")
                    line_tax = (inv_line_subtotal * inv_tax_rate).quantize(Decimal("0.01"))
                    total_monetary_variance += (inv_line_subtotal + line_tax)
                    line_matches.append(
                        LineItemMatch(
                            line_number=inv_line.line_number,
                            description=inv_line.description,
                            invoice_quantity=inv_qty,
                            invoice_unit_price=inv_price,
                            price_variance=Decimal("0.00"),
                            quantity_variance=inv_qty,
                            status="UNMATCHED",
                        )
                    )
        else:
            # Invoice has no itemized lines in DB, check overall total
            inv_tot = invoice.total_amount if invoice.total_amount is not None else Decimal("0.00")
            diff_tot = inv_tot - po.total_amount
            if diff_tot > self.amount_tolerance_val:
                has_price_variance = True
                total_monetary_variance = diff_tot
                discrepancies.append(
                    f"Invoice total ({inv_tot}) exceeds PO #{po.po_number} total ({po.total_amount}) by {diff_tot}."
                )

        # 6. Overall Status Determination
        inv_tot = invoice.total_amount if invoice.total_amount is not None else Decimal("0.00")

        if has_quantity_variance:
            match_status = "QUANTITY_VARIANCE"
            summary = f"Match Failed: Invoiced quantities exceed warehouse accepted receipts on GRNs: {', '.join(grn_numbers)}."
            total_variance = total_monetary_variance
        elif has_price_variance:
            match_status = "PRICE_VARIANCE"
            summary = f"Match Failed: Invoiced price exceeds authorized rate on PO #{po.po_number}."
            total_variance = total_monetary_variance
        elif has_unmatched_lines:
            match_status = "DISCREPANCY"
            summary = f"Match Failed: Invoice contains line items not present on PO #{po.po_number}."
            total_variance = total_monetary_variance
        elif discrepancies:
            match_status = "DISCREPANCY"
            summary = f"Match Discrepancy: {'; '.join(discrepancies)}."
            total_variance = total_monetary_variance
        elif is_partial:
            match_status = "PARTIAL_MATCH"
            summary = f"Partial Delivery Match: Invoiced quantities match partial delivery accepted on GRNs: {', '.join(grn_numbers)}."
            total_variance = Decimal("0.00")
        else:
            match_status = "FULL_MATCH"
            summary = f"Three-way match successful! Invoice #{invoice.invoice_number} perfectly reconciles with PO #{po.po_number} and GRNs ({', '.join(grn_numbers)})."
            total_variance = Decimal("0.00")

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
