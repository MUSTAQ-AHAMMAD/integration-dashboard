"""Flask routes – serves the dashboard page and JSON API endpoints."""

import datetime
import logging

from flask import Blueprint, jsonify, render_template, current_app

from app.db import get_connection
from app.queries import (
    get_integration_status,
    get_overall_kpis,
    get_region_summary,
    get_table_error_summary,
    get_table_errors,
)

logger = logging.getLogger(__name__)

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
    try:
        return jsonify(get_overall_kpis())
    except Exception:
        logger.exception("Failed to fetch KPIs")
        return jsonify({"error": "Database error: unable to fetch KPIs"}), 500


@main_bp.route("/api/integration-status")
def api_integration_status():
    try:
        return jsonify(get_integration_status())
    except Exception:
        logger.exception("Failed to fetch integration status")
        return jsonify({"error": "Database error: unable to fetch integration status"}), 500


@main_bp.route("/api/region-summary")
def api_region_summary():
    try:
        return jsonify(get_region_summary())
    except Exception:
        logger.exception("Failed to fetch region summary")
        return jsonify({"error": "Database error: unable to fetch region summary"}), 500


@main_bp.route("/api/table-errors")
def api_table_errors():
    try:
        return jsonify(get_table_error_summary())
    except Exception:
        logger.exception("Failed to fetch table error summary")
        return jsonify({"error": "Database error: unable to fetch table errors"}), 500


@main_bp.route("/api/table-errors/<table_name>")
def api_table_errors_detail(table_name):
    try:
        return jsonify(get_table_errors(table_name))
    except Exception:
        logger.exception("Failed to fetch table error details")
        return jsonify({"error": "Database error: unable to fetch table error details"}), 500


# ── Health check endpoint ──────────────────────────────────────────────
@main_bp.route("/api/health")
def api_health():
    """Check database connectivity and return status."""
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "ok", "database": "connected"})
    except Exception as exc:
        logger.exception("Health check failed")
        return jsonify({"status": "error", "database": "disconnected", "detail": str(exc)}), 500
