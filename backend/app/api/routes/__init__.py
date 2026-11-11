from fastapi import APIRouter

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.invoices import router as invoices_router
from app.api.routes.departments import router as departments_router
from app.api.routes.vendors import router as vendors_router
from app.api.routes.purchase_orders import router as purchase_orders_router
from app.api.routes.goods_receipts import router as goods_receipts_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.payments import router as payments_router
from app.api.routes.fraud import router as fraud_router
from app.api.routes.audit import router as audit_router
from app.api.routes.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(dashboard_router)
api_router.include_router(invoices_router)
api_router.include_router(departments_router)
api_router.include_router(vendors_router)
api_router.include_router(purchase_orders_router)
api_router.include_router(goods_receipts_router)
api_router.include_router(budgets_router)
api_router.include_router(approvals_router)
api_router.include_router(payments_router)
api_router.include_router(fraud_router)
api_router.include_router(audit_router)
api_router.include_router(users_router)

__all__ = ["api_router"]

