from datetime import date, datetime, timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account_mapping import AccountMapping
from app.models.chart_of_account import ChartOfAccount
from app.models.invoice import Invoice, InvoiceLine
from app.models.journal_entry import JournalEntry, JournalEntryLine

logger = logging.getLogger("bahi_ai.erp.accounting_engine")


class AccountingEngine:
    """Core Double-Entry Accounting Engine for University Accounts Payable.
    Generates balanced, auditable journal entries with debits and credits
    for approved invoices, supporting multi-line expense distributions,
    statutory GST breakdowns (CGST, SGST, IGST), rounding adjustments,
    and reversible vouchers.
    """

    def __init__(self):
        pass

    def _get_account_by_code(self, code: str, db: Session) -> ChartOfAccount:
        """Helper to get an account by code with fallback."""
        acc = db.query(ChartOfAccount).filter(ChartOfAccount.account_code == code).first()
        if not acc:
            raise ValueError(f"Required Chart of Account with code '{code}' not found in database.")
        return acc

    def _get_mapping(self, mapping_type: str, db: Session, entity_id: Optional[int] = None) -> Optional[AccountMapping]:
        """Looks up an active account mapping by type and entity."""
        query = db.query(AccountMapping).filter(
            AccountMapping.mapping_type == mapping_type,
            AccountMapping.is_active.is_(True),
        )
        if entity_id:
            specific = query.filter(AccountMapping.entity_id == entity_id).first()
            if specific:
                return specific
        return query.first()

    def generate_journal_entry_for_invoice(
        self,
        invoice: Invoice,
        db: Session,
        user_id: Optional[int] = None,
    ) -> JournalEntry:
        """Constructs a balanced double-entry journal voucher for an approved invoice."""
        logger.info(f"[AccountingEngine] Generating journal entry for Invoice #{invoice.invoice_number} (ID: {invoice.id})")

        posting_date = invoice.invoice_date or date.today()
        if isinstance(posting_date, str):
            try:
                posting_date = date.fromisoformat(posting_date)
            except Exception:
                posting_date = date.today()

        period = f"{posting_date.year}-{posting_date.month:02d}"

        # 1. Accounts Payable Liability Account (Credit side)
        ap_mapping = self._get_mapping("DEFAULT_AP", db)
        if ap_mapping and ap_mapping.credit_account_id:
            ap_account = db.query(ChartOfAccount).filter(ChartOfAccount.id == ap_mapping.credit_account_id).first()
        else:
            ap_account = self._get_account_by_code("2101", db)

        # 2. Expense Account(s) (Debit side)
        # Check department or category mapping, or fallback to 5001 Office Supplies
        default_exp_account = self._get_account_by_code("5001", db)
        it_exp_account = self._get_account_by_code("5004", db)
        equip_exp_account = self._get_account_by_code("5002", db)

        # 3. Tax Accounts (Debit side - Asset / Input Credit)
        cgst_account = self._get_account_by_code("1401", db)
        sgst_account = self._get_account_by_code("1402", db)
        igst_account = self._get_account_by_code("1403", db)
        roundoff_account = self._get_account_by_code("5099", db)

        # Generate guaranteed unique sequential entry number
        max_id = db.query(func.coalesce(func.max(JournalEntry.id), 0)).scalar() or 0
        candidate_num = max_id + 1
        while db.query(JournalEntry.id).filter(JournalEntry.entry_number == f"JE-{posting_date.year}-{candidate_num:05d}").first():
            candidate_num += 1
        entry_number = f"JE-{posting_date.year}-{candidate_num:05d}"

        description = (
            f"AP Invoice Voucher #{invoice.invoice_number} — "
            f"Vendor: {invoice.vendor.legal_name if invoice.vendor else 'Direct Vendor'} — "
            f"Dept: {invoice.department.name if invoice.department else 'University'}"
        )

        inv_id = invoice.id if (invoice.id and db.query(Invoice.id).filter(Invoice.id == invoice.id).first()) else None
        entry = JournalEntry(
            entry_number=entry_number,
            invoice_id=inv_id,
            posting_date=posting_date,
            accounting_period=period,
            description=description,
            status="POSTED",
            created_by=user_id,
        )

        lines: List[JournalEntryLine] = []
        line_num = 1
        total_debits = Decimal("0.00")

        # Determine taxable subtotal and tax amounts
        grand_total = Decimal(str(invoice.total_amount or "0.00"))
        tax_total = Decimal(str(invoice.tax_amount or "0.00"))
        subtotal = Decimal(str(invoice.subtotal or "0.00"))
        if subtotal <= Decimal("0.00"):
            subtotal = grand_total - tax_total

        # 4. Generate Expense Lines (Debits)
        lines: List[JournalEntryLine] = []
        line_num = 1
        total_debits = Decimal("0.00")

        if invoice.lines and len(invoice.lines) > 0:
            lines_sum = sum(Decimal(str(l.line_total or "0.00")) for l in invoice.lines)
            
            # Check if lines sum to grand_total (gross inclusive of tax) or to subtotal
            lines_inclusive_of_tax = abs(lines_sum - grand_total) <= Decimal("0.05") and tax_total > Decimal("0.00")
            
            for inv_line in invoice.lines:
                desc_lower = inv_line.description.lower()
                chosen_acc = default_exp_account
                if any(k in desc_lower for k in ["computer", "laptop", "software", "server", "license", "cloud"]):
                    chosen_acc = it_exp_account
                elif any(k in desc_lower for k in ["equipment", "lab", "hardware", "machinery", "device"]):
                    chosen_acc = equip_exp_account

                raw_line_amt = Decimal(str(inv_line.line_total or "0.00"))
                if lines_inclusive_of_tax and lines_sum > Decimal("0.00"):
                    # Scale down line to its pre-tax expense component
                    line_expense_amt = (raw_line_amt * (subtotal / lines_sum)).quantize(Decimal("0.01"))
                else:
                    line_expense_amt = raw_line_amt

                if line_expense_amt > Decimal("0.00"):
                    lines.append(
                        JournalEntryLine(
                            line_number=line_num,
                            account_id=chosen_acc.id,
                            description=f"{inv_line.description} (Item #{inv_line.line_number})",
                            debit_amount=line_expense_amt,
                            credit_amount=Decimal("0.00"),
                            department_id=invoice.department_id,
                            vendor_id=invoice.vendor_id,
                        )
                    )
                    line_num += 1
                    total_debits += line_expense_amt
        else:
            # Fallback to taxable subtotal
            if subtotal > Decimal("0.00"):
                lines.append(
                    JournalEntryLine(
                        line_number=line_num,
                        account_id=default_exp_account.id,
                        description=f"Invoiced expenses ({invoice.description or 'Invoice subtotal'})",
                        debit_amount=subtotal,
                        credit_amount=Decimal("0.00"),
                        department_id=invoice.department_id,
                        vendor_id=invoice.vendor_id,
                    )
                )
                line_num += 1
                total_debits += subtotal

        # 5. Generate Tax Lines (Debits)
        gst_breakdown = (invoice.extraction_metadata or {}).get("gst_breakdown") or {}
        cgst_val = Decimal(str(gst_breakdown.get("cgst_amount") or "0.00"))
        sgst_val = Decimal(str(gst_breakdown.get("sgst_amount") or "0.00"))
        igst_val = Decimal(str(gst_breakdown.get("igst_amount") or "0.00"))

        if cgst_val > Decimal("0.00"):
            lines.append(
                JournalEntryLine(
                    line_number=line_num,
                    account_id=cgst_account.id,
                    description=f"Input CGST Tax Credit — Invoice #{invoice.invoice_number}",
                    debit_amount=cgst_val,
                    credit_amount=Decimal("0.00"),
                    department_id=invoice.department_id,
                    vendor_id=invoice.vendor_id,
                )
            )
            line_num += 1
            total_debits += cgst_val

        if sgst_val > Decimal("0.00"):
            lines.append(
                JournalEntryLine(
                    line_number=line_num,
                    account_id=sgst_account.id,
                    description=f"Input SGST Tax Credit — Invoice #{invoice.invoice_number}",
                    debit_amount=sgst_val,
                    credit_amount=Decimal("0.00"),
                    department_id=invoice.department_id,
                    vendor_id=invoice.vendor_id,
                )
            )
            line_num += 1
            total_debits += sgst_val

        if igst_val > Decimal("0.00"):
            lines.append(
                JournalEntryLine(
                    line_number=line_num,
                    account_id=igst_account.id,
                    description=f"Input IGST Tax Credit — Invoice #{invoice.invoice_number}",
                    debit_amount=igst_val,
                    credit_amount=Decimal("0.00"),
                    department_id=invoice.department_id,
                    vendor_id=invoice.vendor_id,
                )
            )
            line_num += 1
            total_debits += igst_val

        # If general tax amount is non-zero but specific GST wasn't in metadata
        allocated_tax = cgst_val + sgst_val + igst_val
        if tax_total > Decimal("0.00") and allocated_tax == Decimal("0.00"):
            half_tax = (tax_total / Decimal("2.00")).quantize(Decimal("0.01"))
            other_half = tax_total - half_tax
            lines.append(
                JournalEntryLine(
                    line_number=line_num,
                    account_id=cgst_account.id,
                    description=f"Input CGST (50%) — Invoice #{invoice.invoice_number}",
                    debit_amount=half_tax,
                    credit_amount=Decimal("0.00"),
                    department_id=invoice.department_id,
                    vendor_id=invoice.vendor_id,
                )
            )
            line_num += 1
            lines.append(
                JournalEntryLine(
                    line_number=line_num,
                    account_id=sgst_account.id,
                    description=f"Input SGST (50%) — Invoice #{invoice.invoice_number}",
                    debit_amount=other_half,
                    credit_amount=Decimal("0.00"),
                    department_id=invoice.department_id,
                    vendor_id=invoice.vendor_id,
                )
            )
            line_num += 1
            total_debits += tax_total

        # 6. Accounts Payable Credit Line (Grand Total)
        grand_total = Decimal(str(invoice.total_amount or "0.00"))
        lines.append(
            JournalEntryLine(
                line_number=line_num,
                account_id=ap_account.id,
                description=f"Accounts Payable Liability — Vendor #{invoice.vendor_id or 'General'}",
                debit_amount=Decimal("0.00"),
                credit_amount=grand_total,
                department_id=invoice.department_id,
                vendor_id=invoice.vendor_id,
            )
        )
        total_credits = grand_total

        # 7. Balancing & Rounding Check
        # Discrepancies between calculated sum of lines and invoiced total are balanced via 5099
        diff = total_credits - total_debits
        if diff != Decimal("0.00"):
            if abs(diff) <= Decimal("5.00"):  # reasonable rounding window
                if diff > Decimal("0.00"):
                    # Debits were less than Credit -> add debit rounding expense
                    line_num += 1
                    lines.append(
                        JournalEntryLine(
                            line_number=line_num,
                            account_id=roundoff_account.id,
                            description="Fractional invoice round-off adjustment",
                            debit_amount=diff,
                            credit_amount=Decimal("0.00"),
                            department_id=invoice.department_id,
                            vendor_id=invoice.vendor_id,
                        )
                    )
                    total_debits += diff
                else:
                    # Debits were more than Credit -> add credit rounding deduction
                    line_num += 1
                    credit_adj = abs(diff)
                    lines.append(
                        JournalEntryLine(
                            line_number=line_num,
                            account_id=roundoff_account.id,
                            description="Fractional invoice discount / rounding adjustment",
                            debit_amount=Decimal("0.00"),
                            credit_amount=credit_adj,
                            department_id=invoice.department_id,
                            vendor_id=invoice.vendor_id,
                        )
                    )
                    total_credits += credit_adj
            else:
                logger.warning(
                    f"[AccountingEngine] Large variance between Debits ({total_debits}) "
                    f"and Credits ({total_credits})."
                )

        entry.total_debit = total_debits
        entry.total_credit = total_credits
        entry.is_balanced = total_debits == total_credits
        entry.lines = lines

        db.add(entry)
        db.flush()
        return entry

    def generate_reversal_entry(
        self,
        original_entry: JournalEntry,
        db: Session,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> JournalEntry:
        """Constructs an inverted reversal journal entry for a previously posted entry."""
        logger.info(f"[AccountingEngine] Reversing Journal Entry #{original_entry.entry_number}")

        today = date.today()
        period = f"{today.year}-{today.month:02d}"

        reversal_num = f"REV-{original_entry.entry_number}"
        suffix = 1
        candidate_rev = reversal_num
        while db.query(JournalEntry.id).filter(JournalEntry.entry_number == candidate_rev).first():
            candidate_rev = f"{reversal_num}-{suffix}"
            suffix += 1
        reversal_num = candidate_rev

        reversal = JournalEntry(
            entry_number=reversal_num,
            invoice_id=original_entry.invoice_id,
            posting_date=today,
            accounting_period=period,
            description=f"REVERSAL of {original_entry.entry_number}: {reason or original_entry.description}",
            total_debit=original_entry.total_credit,
            total_credit=original_entry.total_debit,
            is_balanced=original_entry.is_balanced,
            status="POSTED",
            reversal_of_id=original_entry.id,
            created_by=user_id,
        )

        reversal_lines: List[JournalEntryLine] = []
        for orig_line in original_entry.lines:
            reversal_lines.append(
                JournalEntryLine(
                    line_number=orig_line.line_number,
                    account_id=orig_line.account_id,
                    description=f"REVERSAL: {orig_line.description}",
                    # Swap debit and credit
                    debit_amount=orig_line.credit_amount,
                    credit_amount=orig_line.debit_amount,
                    department_id=orig_line.department_id,
                    vendor_id=orig_line.vendor_id,
                )
            )

        reversal.lines = reversal_lines
        original_entry.status = "REVERSED"

        db.add(reversal)
        db.flush()
        return reversal
