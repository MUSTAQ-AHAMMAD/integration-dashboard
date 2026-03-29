"""Flask routes – serves the dashboard page and JSON API endpoints."""

import datetime

from flask import Blueprint, jsonify, render_template, current_app

from app.queries import (
    get_integration_status,
    get_overall_kpis,
    get_region_summary,
    get_table_error_summary,
    get_table_errors,
)

main_bp = Blueprint("main", __name__)


# ── Dashboard page ─────────────────────────────────────────────────────
@main_bp.route("/")
def dashboard():
    """Render the main dashboard page."""
    return render_template(
        "dashboard.html",
        refresh_interval=current_app.config.get("REFRESH_INTERVAL", 30),
        current_year=datetime.datetime.now(datetime.timezone.utc).year,
    )


# ── JSON API endpoints (consumed by the front-end via fetch) ───────────
@main_bp.route("/api/kpis")
def api_kpis():
    return jsonify(get_overall_kpis())


@main_bp.route("/api/integration-status")
def api_integration_status():
    return jsonify(get_integration_status())


@main_bp.route("/api/region-summary")
def api_region_summary():
    return jsonify(get_region_summary())


@main_bp.route("/api/table-errors")
def api_table_errors():
    return jsonify(get_table_error_summary())


@main_bp.route("/api/table-errors/<table_name>")
def api_table_errors_detail(table_name):
    return jsonify(get_table_errors(table_name))
