import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_budgets():
    response = client.get("/api/v1/budgets")
    assert response.status_code == 200
    budgets = response.json()
    assert len(budgets) >= 5
    for b in budgets:
        assert float(b["allocated_amount"]) > 0
        assert float(b["available_amount"]) >= 0


def test_get_departments():
    response = client.get("/api/v1/departments")
    assert response.status_code == 200
    depts = response.json()
    assert len(depts) >= 5
    codes = [d["code"] for d in depts]
    assert "CSE" in codes
    assert "ADMIN" in codes

