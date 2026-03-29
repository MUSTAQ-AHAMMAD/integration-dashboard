"""Tests for the dashboard routes."""

from unittest.mock import patch


# ── Dashboard page ─────────────────────────────────────────────────────
def test_dashboard_renders(client):
    """GET / should return the dashboard HTML page."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Integration Dashboard" in resp.data


def test_dashboard_contains_kpi_cards(client):
    """The dashboard page should contain KPI card placeholders."""
    resp = client.get("/")
    html = resp.data.decode()
    assert 'id="kpi-total"' in html
    assert 'id="kpi-running"' in html
    assert 'id="kpi-stopped"' in html
    assert 'id="kpi-error"' in html


def test_dashboard_contains_chart_canvases(client):
    """The dashboard page should contain chart canvas elements."""
    resp = client.get("/")
    html = resp.data.decode()
    assert 'id="statusPieChart"' in html
    assert 'id="regionBarChart"' in html


def test_dashboard_includes_refresh_interval(client):
    """The dashboard injects the server-configured refresh interval."""
    resp = client.get("/")
    html = resp.data.decode()
    assert "window.REFRESH_INTERVAL" in html


# ── API: /api/kpis ────────────────────────────────────────────────────
@patch("app.routes.get_overall_kpis")
def test_api_kpis(mock_kpis, client):
    mock_kpis.return_value = {"total": 12, "running": 8, "stopped": 3, "error": 1}
    resp = client.get("/api/kpis")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 12
    assert data["running"] == 8


# ── API: /api/integration-status ──────────────────────────────────────
@patch("app.routes.get_integration_status")
def test_api_integration_status(mock_status, client):
    mock_status.return_value = [
        {
            "region": "US",
            "integration_name": "Invoice Sync",
            "status": "running",
            "last_run_time": "2026-03-29T04:00:00",
            "error_message": None,
            "updated_at": "2026-03-29T04:00:00",
        }
    ]
    resp = client.get("/api/integration-status")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 1
    assert rows[0]["region"] == "US"


# ── API: /api/region-summary ──────────────────────────────────────────
@patch("app.routes.get_region_summary")
def test_api_region_summary(mock_region, client):
    mock_region.return_value = [
        {"region": "US", "total": 5, "running": 3, "stopped": 1, "error": 1},
        {"region": "EU", "total": 4, "running": 4, "stopped": 0, "error": 0},
    ]
    resp = client.get("/api/region-summary")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert len(rows) == 2
    assert rows[1]["region"] == "EU"


# ── API: /api/table-errors ───────────────────────────────────────────
@patch("app.routes.get_table_error_summary")
def test_api_table_errors(mock_table, client):
    mock_table.return_value = [
        {"table": "fusion_invoice_header", "status_counts": [{"status": "error", "count": 5}]}
    ]
    resp = client.get("/api/table-errors")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data[0]["table"] == "fusion_invoice_header"


# ── API: /api/table-errors/<name> ────────────────────────────────────
@patch("app.routes.get_table_errors")
def test_api_table_errors_detail(mock_detail, client):
    mock_detail.return_value = [{"id": 1, "status": "error", "error_message": "timeout"}]
    resp = client.get("/api/table-errors/fusion_invoice_header")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data[0]["status"] == "error"


@patch("app.routes.get_table_errors")
def test_api_table_errors_detail_invalid_table(mock_detail, client):
    """An unknown table name should return an empty list."""
    mock_detail.return_value = []
    resp = client.get("/api/table-errors/nonexistent_table")
    assert resp.status_code == 200
    assert resp.get_json() == []


# ── Modern UI elements ────────────────────────────────────────────────
def test_dashboard_contains_search_input(client):
    """The dashboard should have a search/filter input for integration status."""
    resp = client.get("/")
    html = resp.data.decode()
    assert 'id="status-search"' in html


def test_dashboard_contains_skeleton_loaders(client):
    """The dashboard should have skeleton loading placeholders."""
    resp = client.get("/")
    html = resp.data.decode()
    assert "skeleton" in html


def test_dashboard_contains_entrance_animations(client):
    """The dashboard should have entrance animation CSS classes."""
    resp = client.get("/")
    html = resp.data.decode()
    assert "animate-in" in html


def test_dashboard_contains_footer(client):
    """The dashboard should have a footer section."""
    resp = client.get("/")
    html = resp.data.decode()
    assert "dashboard-footer" in html


def test_dashboard_contains_toast_container(client):
    """The dashboard should have a toast notification container."""
    resp = client.get("/")
    html = resp.data.decode()
    assert 'id="toast-container"' in html


def test_dashboard_contains_current_year(client):
    """The dashboard footer should contain the current year."""
    import datetime

    resp = client.get("/")
    html = resp.data.decode()
    current_year = str(datetime.datetime.now(datetime.timezone.utc).year)
    assert current_year in html
