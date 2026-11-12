from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.account_mapping import AccountMapping
from app.models.chart_of_account import ChartOfAccount
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.schemas.erp import (
    AccountMappingCreate,
    AccountMappingResponse,
    AccountMappingUpdate,
    ChartOfAccountCreate,
    ChartOfAccountResponse,
    JournalEntryDetailResponse,
    JournalEntryLineResponse,
    JournalEntryResponse,
    TrialBalanceAccount,
    TrialBalanceResponse,
)
from app.services.erp.accounting_engine import AccountingEngine

router = APIRouter(prefix="/ledger", tags=["General Ledger & Accounting"])


@router.get("/accounts", response_model=List[ChartOfAccountResponse])
def list_chart_of_accounts(
    account_type: Optional[str] = Query(None, description="Filter by type: ASSET, LIABILITY, EXPENSE, REVENUE, EQUITY"),
    db: Session = Depends(get_db),
):
    """Returns university Chart of Accounts with aggregated debit and credit balances."""
    query = db.query(ChartOfAccount)
    if account_type:
        query = query.filter(ChartOfAccount.account_type == account_type.upper())

    accounts = query.order_by(ChartOfAccount.account_code.asc()).all()

    # Aggregate line sums per account
    balances = (
        db.query(
            JournalEntryLine.account_id,
            func.coalesce(func.sum(JournalEntryLine.debit_amount), Decimal("0.00")).label("total_debit"),
            func.coalesce(func.sum(JournalEntryLine.credit_amount), Decimal("0.00")).label("total_credit"),
        )
        .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
        .filter(JournalEntry.status != "DRAFT")
        .group_by(JournalEntryLine.account_id)
        .all()
    )
    balance_map = {b[0]: (b[1], b[2]) for b in balances}

    result: List[ChartOfAccountResponse] = []
    for acc in accounts:
        deb, cred = balance_map.get(acc.id, (Decimal("0.00"), Decimal("0.00")))
        net = (deb - cred) if acc.account_type in ["ASSET", "EXPENSE"] else (cred - deb)
        result.append(
            ChartOfAccountResponse(
                id=acc.id,
                account_code=acc.account_code,
                account_name=acc.account_name,
                account_type=acc.account_type,
                description=acc.description,
                is_active=acc.is_active,
                created_at=acc.created_at,
                updated_at=acc.updated_at,
                debit_balance=deb,
                credit_balance=cred,
                net_balance=net,
            )
        )
    return result


@router.post("/accounts", response_model=ChartOfAccountResponse, status_code=status.HTTP_201_CREATED)
def create_chart_of_account(acc_in: ChartOfAccountCreate, db: Session = Depends(get_db)):
    """Creates a new Chart of Account code."""
    existing = db.query(ChartOfAccount).filter(ChartOfAccount.account_code == acc_in.account_code.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Account code '{acc_in.account_code}' already exists.")

    acc = ChartOfAccount(
        account_code=acc_in.account_code.strip(),
        account_name=acc_in.account_name.strip(),
        account_type=acc_in.account_type.upper().strip(),
        description=acc_in.description,
        is_active=acc_in.is_active,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return ChartOfAccountResponse(
        id=acc.id,
        account_code=acc.account_code,
        account_name=acc.account_name,
        account_type=acc.account_type,
        description=acc.description,
        is_active=acc.is_active,
        created_at=acc.created_at,
        updated_at=acc.updated_at,
        debit_balance=Decimal("0.00"),
        credit_balance=Decimal("0.00"),
        net_balance=Decimal("0.00"),
    )


@router.get("/mappings", response_model=List[AccountMappingResponse])
def list_account_mappings(db: Session = Depends(get_db)):
    """Returns active accounting GL distribution mappings."""
    return (
        db.query(AccountMapping)
        .options(
            joinedload(AccountMapping.debit_account),
            joinedload(AccountMapping.credit_account),
        )
        .order_by(AccountMapping.id.asc())
        .all()
    )


@router.post("/mappings", response_model=AccountMappingResponse, status_code=status.HTTP_201_CREATED)
def create_account_mapping(mapping_in: AccountMappingCreate, db: Session = Depends(get_db)):
    """Creates a new accounting mapping rule."""
    mapping = AccountMapping(
        mapping_type=mapping_in.mapping_type.upper().strip(),
        entity_id=mapping_in.entity_id,
        expense_category=mapping_in.expense_category,
        debit_account_id=mapping_in.debit_account_id,
        credit_account_id=mapping_in.credit_account_id,
        description=mapping_in.description,
        is_active=mapping_in.is_active,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.put("/mappings/{mapping_id}", response_model=AccountMappingResponse)
def update_account_mapping(
    mapping_id: int,
    mapping_in: AccountMappingUpdate,
    db: Session = Depends(get_db),
):
    """Updates an existing accounting mapping rule."""
    mapping = db.query(AccountMapping).filter(AccountMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found.")

    if mapping_in.debit_account_id is not None:
        mapping.debit_account_id = mapping_in.debit_account_id
    if mapping_in.credit_account_id is not None:
        mapping.credit_account_id = mapping_in.credit_account_id
    if mapping_in.expense_category is not None:
        mapping.expense_category = mapping_in.expense_category
    if mapping_in.description is not None:
        mapping.description = mapping_in.description
    if mapping_in.is_active is not None:
        mapping.is_active = mapping_in.is_active

    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/journal-entries", response_model=List[JournalEntryResponse])
def list_journal_entries(
    status: Optional[str] = Query(None, description="Filter by status: POSTED, REVERSED, DRAFT"),
    period: Optional[str] = Query(None, description="Filter by accounting period (e.g. 2026-11)"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Returns journal entry vouchers from general ledger."""
    query = (
        db.query(JournalEntry)
        .options(
            joinedload(JournalEntry.erp_postings),
        )
    )
    if status:
        query = query.filter(JournalEntry.status == status.upper())
    if period:
        query = query.filter(JournalEntry.accounting_period == period)
    if invoice_id:
        query = query.filter(JournalEntry.invoice_id == invoice_id)

    entries = query.order_by(JournalEntry.posting_date.desc(), JournalEntry.id.desc()).offset(skip).limit(limit).all()

    result: List[JournalEntryResponse] = []
    for e in entries:
        doc_ref = e.erp_postings[0].erp_document_reference if e.erp_postings else None
        res_item = JournalEntryResponse(
            id=e.id,
            entry_number=e.entry_number,
            invoice_id=e.invoice_id,
            posting_date=e.posting_date,
            accounting_period=e.accounting_period,
            description=e.description,
            total_debit=e.total_debit,
            total_credit=e.total_credit,
            is_balanced=e.is_balanced,
            status=e.status,
            reversal_of_id=e.reversal_of_id,
            erp_document_reference=doc_ref,
            created_by=e.created_by,
            created_at=e.created_at,
        )
        result.append(res_item)
    return result


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryDetailResponse)
def get_journal_entry_detail(entry_id: int, db: Session = Depends(get_db)):
    """Returns complete journal entry details including itemized debit and credit lines."""
    entry = (
        db.query(JournalEntry)
        .options(
            joinedload(JournalEntry.lines).joinedload(JournalEntryLine.account),
            joinedload(JournalEntry.erp_postings),
        )
        .filter(JournalEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")

    doc_ref = entry.erp_postings[0].erp_document_reference if entry.erp_postings else None
    lines: List[JournalEntryLineResponse] = []
    for l in entry.lines:
        lines.append(
            JournalEntryLineResponse(
                id=l.id,
                journal_entry_id=l.journal_entry_id,
                line_number=l.line_number,
                account_id=l.account_id,
                account_code=l.account.account_code if l.account else None,
                account_name=l.account.account_name if l.account else None,
                account_type=l.account.account_type if l.account else None,
                description=l.description,
                debit_amount=l.debit_amount,
                credit_amount=l.credit_amount,
                department_id=l.department_id,
                vendor_id=l.vendor_id,
            )
        )

    return JournalEntryDetailResponse(
        id=entry.id,
        entry_number=entry.entry_number,
        invoice_id=entry.invoice_id,
        posting_date=entry.posting_date,
        accounting_period=entry.accounting_period,
        description=entry.description,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
        is_balanced=entry.is_balanced,
        status=entry.status,
        reversal_of_id=entry.reversal_of_id,
        erp_document_reference=doc_ref,
        created_by=entry.created_by,
        created_at=entry.created_at,
        lines=lines,
    )


@router.post("/journal-entries/{entry_id}/reverse", response_model=JournalEntryResponse)
def reverse_journal_entry(
    entry_id: int,
    reason: Optional[str] = Query(None, description="Reason for journal reversal"),
    db: Session = Depends(get_db),
):
    """Generates an inverted reversal entry for a posted journal voucher."""
    entry = (
        db.query(JournalEntry)
        .options(joinedload(JournalEntry.lines))
        .filter(JournalEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")

    if entry.status == "REVERSED":
        raise HTTPException(status_code=400, detail="Journal entry is already reversed.")

    engine = AccountingEngine()
    reversal = engine.generate_reversal_entry(entry, db, reason=reason)
    db.commit()
    db.refresh(reversal)

    return JournalEntryResponse(
        id=reversal.id,
        entry_number=reversal.entry_number,
        invoice_id=reversal.invoice_id,
        posting_date=reversal.posting_date,
        accounting_period=reversal.accounting_period,
        description=reversal.description,
        total_debit=reversal.total_debit,
        total_credit=reversal.total_credit,
        is_balanced=reversal.is_balanced,
        status=reversal.status,
        reversal_of_id=reversal.reversal_of_id,
        created_by=reversal.created_by,
        created_at=reversal.created_at,
    )


@router.get("/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    period: Optional[str] = Query(None, description="Filter by accounting period (e.g. 2026-11)"),
    db: Session = Depends(get_db),
):
    """Calculates general ledger trial balance with double-entry integrity verification."""
    query = (
        db.query(
            ChartOfAccount.id,
            ChartOfAccount.account_code,
            ChartOfAccount.account_name,
            ChartOfAccount.account_type,
            func.coalesce(func.sum(JournalEntryLine.debit_amount), Decimal("0.00")).label("total_debit"),
            func.coalesce(func.sum(JournalEntryLine.credit_amount), Decimal("0.00")).label("total_credit"),
        )
        .outerjoin(JournalEntryLine, ChartOfAccount.id == JournalEntryLine.account_id)
        .outerjoin(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
    )

    if period:
        query = query.filter(JournalEntry.accounting_period == period)

    # Exclude drafts
    query = query.filter((JournalEntry.status != "DRAFT") | (JournalEntry.status.is_(None)))

    results = query.group_by(
        ChartOfAccount.id,
        ChartOfAccount.account_code,
        ChartOfAccount.account_name,
        ChartOfAccount.account_type,
    ).order_by(ChartOfAccount.account_code.asc()).all()

    tb_accounts: List[TrialBalanceAccount] = []
    grand_debit = Decimal("0.00")
    grand_credit = Decimal("0.00")

    for r in results:
        acc_id, code, name, acc_type, deb, cred = r
        deb_dec = Decimal(str(deb))
        cred_dec = Decimal(str(cred))
        grand_debit += deb_dec
        grand_credit += cred_dec

        if acc_type in ["ASSET", "EXPENSE"]:
            net_deb = max(Decimal("0.00"), deb_dec - cred_dec)
            net_cred = max(Decimal("0.00"), cred_dec - deb_dec)
        else:
            net_cred = max(Decimal("0.00"), cred_dec - deb_dec)
            net_deb = max(Decimal("0.00"), deb_dec - cred_dec)

        tb_accounts.append(
            TrialBalanceAccount(
                account_id=acc_id,
                account_code=code,
                account_name=name,
                account_type=acc_type,
                debit_total=deb_dec,
                credit_total=cred_dec,
                net_debit=net_deb,
                net_credit=net_cred,
            )
        )

    is_balanced = (grand_debit == grand_credit)

    return TrialBalanceResponse(
        accounting_period=period,
        as_of_date=date.today(),
        accounts=tb_accounts,
        total_debit=grand_debit,
        total_credit=grand_credit,
        is_balanced=is_balanced,
    )
