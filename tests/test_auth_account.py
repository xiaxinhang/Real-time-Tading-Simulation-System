from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_register_creates_token_account_and_cashflow() -> None:
    client = TestClient(app)
    username = "pytest_user_auth_account"

    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123", "email": "pytest_user@example.com"},
    )
    if response.status_code == 409:
        response = client.post("/api/auth/login", json={"username": username, "password": "secret123"})

    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    account = client.get("/api/account", headers=headers)
    assert account.status_code == 200
    assert account.json()["available_cash"] == 1_000_000.0

    cashflows = client.get("/api/cashflows", headers=headers)
    assert cashflows.status_code == 200
    assert len(cashflows.json()) >= 1
