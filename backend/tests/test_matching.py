import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_purchase_orders_and_goods_receipts():
    po_res = client.get("/api/v1/purchase-orders")
    assert po_res.status_code == 200
    pos = po_res.json()
    assert len(pos) >= 10

    grn_res = client.get("/api/v1/goods-receipts")
    assert grn_res.status_code == 200
    grns = grn_res.json()
    assert len(grns) >= 8

    # Check partial delivery in GRN
    partial_grns = [g for g in grns if g["status"] == "PARTIAL"]
    assert len(partial_grns) > 0


def test_fraud_alerts_and_exceptions():
    res = client.get("/api/v1/fraud-alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 4

    types = [a["alert_type"] for a in alerts]
    assert "DUPLICATE_INVOICE" in types
    assert "OVERBILLING" in types

