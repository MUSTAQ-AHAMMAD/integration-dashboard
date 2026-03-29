"""Tests for authentication and user management."""

import json
import os
import shutil

import pytest
from unittest.mock import patch

from app import create_app
from app import auth as auth_module


@pytest.fixture()
def app(tmp_path):
    """Create a Flask app with a temporary instance folder for user storage."""
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "DB_HOST": "localhost",
        "DB_PORT": "1521",
        "DB_SERVICE_NAME": "ORCL",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "DB_MODE": "SYSDBA",
        "REFRESH_INTERVAL": 10,
    }
    app = create_app(config=test_config)
    # Override instance path to tmp_path for isolation
    app.instance_path = str(tmp_path)
    auth_module._users_file = os.path.join(str(tmp_path), "users.json")
    # Clear any default admin from previous init
    auth_module.save_users([])
    auth_module.create_user("admin", "admin123", "admin",
                            ["dashboard", "integration_report", "transaction_report"])
    yield app


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


def _login(client, username="admin", password="admin123"):
    """Helper to log in via POST form."""
    return client.post("/login", data={
        "username": username,
        "password": password,
    }, follow_redirects=True)


# ── Login tests ──────────────────────────────────────────────────────
def test_login_page_renders(client):
    """GET /login should render the login page."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_login_page_shows_default_credentials(client):
    """GET /login should show default admin credentials hint."""
    resp = client.get("/login")
    html = resp.data.decode()
    assert "admin" in html
    assert "admin123" in html


def test_login_success(client):
    """POST /login with valid credentials redirects to dashboard."""
    resp = _login(client)
    assert resp.status_code == 200
    assert b"Integration Command Center" in resp.data


def test_login_failure(client):
    """POST /login with bad credentials returns 401."""
    resp = client.post("/login", data={
        "username": "admin",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401
    assert b"Invalid username or password" in resp.data


def test_dashboard_requires_login(client):
    """GET / should redirect to login when not authenticated."""
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout(client):
    """GET /logout should redirect to login."""
    _login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ── Report pages require login ────────────────────────────────────────
def test_management_dashboard_requires_login(client):
    """GET /management should redirect when not logged in."""
    resp = client.get("/management")
    assert resp.status_code == 302


def test_integration_report_requires_login(client):
    """GET /reports/integration should redirect when not logged in."""
    resp = client.get("/reports/integration")
    assert resp.status_code == 302


def test_transaction_report_requires_login(client):
    """GET /reports/transactions should redirect when not logged in."""
    resp = client.get("/reports/transactions")
    assert resp.status_code == 302


def test_management_dashboard_renders(client):
    """GET /management should render when logged in."""
    _login(client)
    resp = client.get("/management")
    assert resp.status_code == 200
    assert b"Management Dashboard" in resp.data


def test_integration_report_renders(client):
    """GET /reports/integration should render when logged in."""
    _login(client)
    resp = client.get("/reports/integration")
    assert resp.status_code == 200
    assert b"Integration Report" in resp.data


def test_transaction_report_renders(client):
    """GET /reports/transactions should render when logged in."""
    _login(client)
    resp = client.get("/reports/transactions")
    assert resp.status_code == 200
    assert b"Transaction Report" in resp.data


# ── Admin user management ─────────────────────────────────────────────
def test_admin_users_page_requires_login(client):
    """GET /admin/users should redirect when not logged in."""
    resp = client.get("/admin/users")
    assert resp.status_code == 302


def test_admin_users_page_renders(client):
    """GET /admin/users should render for admin."""
    _login(client)
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b"User Management" in resp.data


def test_admin_list_users(client):
    """GET /api/admin/users should return user list without passwords."""
    _login(client)
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 1
    assert data[0]["username"] == "admin"
    assert "password_hash" not in data[0]


def test_admin_create_user(client):
    """POST /api/admin/users should create a new user."""
    _login(client)
    resp = client.post("/api/admin/users",
                       json={"username": "viewer1", "password": "pass123",
                             "role": "viewer", "allowed_pages": ["dashboard"]})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["username"] == "viewer1"
    assert data["role"] == "viewer"


def test_admin_create_duplicate_user(client):
    """POST /api/admin/users with existing username returns 409."""
    _login(client)
    resp = client.post("/api/admin/users",
                       json={"username": "admin", "password": "pass123"})
    assert resp.status_code == 409


def test_admin_update_user(client):
    """PUT /api/admin/users/<id> should update user details."""
    _login(client)
    # Create a user first
    resp = client.post("/api/admin/users",
                       json={"username": "editor", "password": "pass123",
                             "role": "viewer"})
    user_id = resp.get_json()["id"]

    # Update
    resp = client.put(f"/api/admin/users/{user_id}",
                      json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "admin"


def test_admin_delete_user(client):
    """DELETE /api/admin/users/<id> should delete a user."""
    _login(client)
    # Create a user
    resp = client.post("/api/admin/users",
                       json={"username": "temp", "password": "pass123"})
    user_id = resp.get_json()["id"]

    # Delete
    resp = client.delete(f"/api/admin/users/{user_id}")
    assert resp.status_code == 200


def test_admin_cannot_delete_last_admin(client):
    """DELETE should prevent deleting the last admin."""
    _login(client)
    # Get admin user ID
    resp = client.get("/api/admin/users")
    admin_id = resp.get_json()[0]["id"]

    resp = client.delete(f"/api/admin/users/{admin_id}")
    assert resp.status_code == 400
    assert b"last admin" in resp.data


def test_viewer_cannot_access_admin(client):
    """Non-admin users should get 403 on admin endpoints."""
    _login(client)
    # Create viewer
    client.post("/api/admin/users",
                json={"username": "viewer2", "password": "pass123",
                      "role": "viewer"})
    client.get("/logout")

    # Login as viewer
    _login(client, "viewer2", "pass123")
    resp = client.get("/admin/users")
    assert resp.status_code == 403

    resp = client.get("/api/admin/users")
    assert resp.status_code == 403


# ── API region endpoints ─────────────────────────────────────────────
@patch("app.routes.get_available_regions")
def test_api_regions(mock_regions, client):
    """GET /api/regions returns region list."""
    mock_regions.return_value = ["SA", "AE", "KW"]
    resp = client.get("/api/regions")
    assert resp.status_code == 200
    assert resp.get_json() == ["SA", "AE", "KW"]


@patch("app.routes.get_sales_integration_detail")
def test_api_sales_integration_detail(mock_detail, client):
    """GET /api/sales-integration-detail returns status rows."""
    mock_detail.return_value = [
        {"region": "SA", "integ_mode": "AUTOMATIC", "status": "RUNNING"},
        {"region": "SA", "integ_mode": "MANUAL", "status": "IDLE"},
    ]
    resp = client.get("/api/sales-integration-detail")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]["region"] == "SA"


# ── Report API endpoints ─────────────────────────────────────────────
@patch("app.routes.get_fusion_invoice_header_report")
def test_api_invoice_headers(mock_fn, client):
    """GET /api/reports/invoice-headers returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success", "region": "SA"}]
    resp = client.get("/api/reports/invoice-headers?region=SA")
    assert resp.status_code == 200
    assert resp.get_json()[0]["status"] == "Success"


@patch("app.routes.get_fusion_invoice_line_report")
def test_api_invoice_lines(mock_fn, client):
    """GET /api/reports/invoice-lines returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success"}]
    resp = client.get("/api/reports/invoice-lines")
    assert resp.status_code == 200


@patch("app.routes.get_fusion_misc_receipt_report")
def test_api_misc_receipts(mock_fn, client):
    """GET /api/reports/misc-receipts returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success"}]
    resp = client.get("/api/reports/misc-receipts")
    assert resp.status_code == 200


@patch("app.routes.get_fusion_standard_receipt_report")
def test_api_standard_receipts(mock_fn, client):
    """GET /api/reports/standard-receipts returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success"}]
    resp = client.get("/api/reports/standard-receipts")
    assert resp.status_code == 200


@patch("app.routes.get_fusion_apply_receipt_report")
def test_api_apply_receipts(mock_fn, client):
    """GET /api/reports/apply-receipts returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success"}]
    resp = client.get("/api/reports/apply-receipts")
    assert resp.status_code == 200


@patch("app.routes.get_fusion_inv_txn_report")
def test_api_inv_txn(mock_fn, client):
    """GET /api/reports/inv-txn returns data."""
    _login(client)
    mock_fn.return_value = [{"row_id": 1, "status": "Success"}]
    resp = client.get("/api/reports/inv-txn")
    assert resp.status_code == 200


@patch("app.routes.get_table_status_summary")
def test_api_table_summary(mock_fn, client):
    """GET /api/reports/table-summary returns data."""
    _login(client)
    mock_fn.return_value = [{"table": "fusion_invoice_header", "status_counts": []}]
    resp = client.get("/api/reports/table-summary?region=SA")
    assert resp.status_code == 200


def test_report_api_requires_login(client):
    """Report API endpoints should redirect when not logged in."""
    resp = client.get("/api/reports/invoice-headers")
    assert resp.status_code == 302
