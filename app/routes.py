"""Flask routes – serves the dashboard page and JSON API endpoints."""

import datetime
import logging

import oracledb
from flask import Blueprint, jsonify, render_template, current_app, request, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user

from app.db import get_connection, test_connection, _dsn_label
from app.queries import (
    get_integration_status,
    get_management_report,
    get_overall_kpis,
    get_region_summary,
    get_table_error_summary,
    get_table_errors,
    get_available_regions,
    get_sales_integration_detail,
    get_fusion_invoice_header_report,
    get_fusion_invoice_line_report,
    get_fusion_misc_receipt_report,
    get_fusion_standard_receipt_report,
    get_fusion_apply_receipt_report,
    get_fusion_inv_txn_report,
    get_table_status_summary,
)
from app.auth import authenticate, create_user, delete_user, update_user, load_users

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


# ── Dashboard page ─────────────────────────────────────────────────────
@main_bp.route("/")
@login_required
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
    except oracledb.Error:
        logger.exception("Failed to fetch KPIs")
        return jsonify({"error": "Database error: unable to fetch KPIs"}), 500


@main_bp.route("/api/integration-status")
def api_integration_status():
    try:
        return jsonify(get_integration_status())
    except oracledb.Error:
        logger.exception("Failed to fetch integration status")
        return jsonify({"error": "Database error: unable to fetch integration status"}), 500


@main_bp.route("/api/region-summary")
def api_region_summary():
    try:
        return jsonify(get_region_summary())
    except oracledb.Error:
        logger.exception("Failed to fetch region summary")
        return jsonify({"error": "Database error: unable to fetch region summary"}), 500


@main_bp.route("/api/table-errors")
def api_table_errors():
    try:
        return jsonify(get_table_error_summary())
    except oracledb.Error:
        logger.exception("Failed to fetch table error summary")
        return jsonify({"error": "Database error: unable to fetch table errors"}), 500


@main_bp.route("/api/table-errors/<table_name>")
def api_table_errors_detail(table_name):
    try:
        return jsonify(get_table_errors(table_name))
    except oracledb.Error:
        logger.exception("Failed to fetch table error details")
        return jsonify({"error": "Database error: unable to fetch table error details"}), 500


@main_bp.route("/api/management-report")
def api_management_report():
    try:
        return jsonify(get_management_report())
    except oracledb.Error:
        logger.exception("Failed to fetch management report")
        return jsonify({"error": "Database error: unable to fetch management report"}), 500


# ── Health check endpoint ──────────────────────────────────────────────
@main_bp.route("/api/health")
def api_health():
    """Check database connectivity by running a real query."""
    try:
        test_connection()
        return jsonify({
            "status": "ok",
            "database": "connected",
            "target": _dsn_label(),
        })
    except Exception as exc:
        logger.exception("Health check failed")
        error_str = str(exc)
        error_response = {
            "status": "error",
            "database": "disconnected",
            "target": _dsn_label(),
            "detail": error_str,
        }
        if "DPY-4011" in error_str:
            error_response["hint"] = (
                "DPY-4011 indicates the database or network closed the "
                "connection. Check your .env database settings and verify "
                "the database is reachable."
            )
            error_response["help_url"] = (
                "https://python-oracledb.readthedocs.io/en/latest/"
                "user_guide/troubleshooting.html#dpy-4011"
            )
        return jsonify(error_response), 500


# ── Auth routes ────────────────────────────────────────────────────────
@main_bp.route("/login", methods=["GET"])
def login():
    """Render login page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main_bp.route("/login", methods=["POST"])
def login_post():
    """Authenticate user and redirect to dashboard."""
    data = request.form
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = authenticate(username, password)
    if user is None:
        return render_template("login.html", error="Invalid username or password"), 401

    login_user(user)
    return redirect(url_for("main.dashboard"))


@main_bp.route("/logout")
def logout():
    """Logout user and redirect to login."""
    logout_user()
    return redirect(url_for("main.login"))


# ── Report routes ──────────────────────────────────────────────────────
@main_bp.route("/management")
@login_required
def management_dashboard():
    """Render the management dashboard page."""
    return render_template(
        "management_dashboard.html",
        current_year=datetime.datetime.now(datetime.timezone.utc).year,
    )


@main_bp.route("/reports/integration")
@login_required
def integration_report():
    """Render the integration report page."""
    return render_template(
        "integration_report.html",
        current_year=datetime.datetime.now(datetime.timezone.utc).year,
    )


@main_bp.route("/reports/transactions")
@login_required
def transaction_report():
    """Render the transaction report page."""
    return render_template(
        "transaction_report.html",
        current_year=datetime.datetime.now(datetime.timezone.utc).year,
    )


# ── Admin routes ───────────────────────────────────────────────────────
@main_bp.route("/admin/users")
@login_required
def admin_users():
    """Render user management page."""
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    return render_template(
        "admin_users.html",
        current_year=datetime.datetime.now(datetime.timezone.utc).year,
    )


@main_bp.route("/api/admin/users", methods=["GET"])
@login_required
def api_list_users():
    """List all users (no password hashes)."""
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403
    users = load_users()
    safe_users = []
    for u in users:
        safe_users.append({
            "id": u["id"],
            "username": u["username"],
            "role": u["role"],
            "allowed_pages": u["allowed_pages"],
        })
    return jsonify(safe_users)


@main_bp.route("/api/admin/users", methods=["POST"])
@login_required
def api_create_user():
    """Create a new user."""
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "viewer")
    allowed_pages = data.get("allowed_pages", ["dashboard"])

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if role not in ("admin", "viewer"):
        return jsonify({"error": "Role must be 'admin' or 'viewer'"}), 400

    user = create_user(username, password, role, allowed_pages)
    if user is None:
        return jsonify({"error": "Username already exists"}), 409

    return jsonify(user.to_safe_dict()), 201


@main_bp.route("/api/admin/users/<user_id>", methods=["PUT"])
@login_required
def api_update_user(user_id):
    """Update a user."""
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user = update_user(
        user_id,
        username=data.get("username"),
        password=data.get("password"),
        role=data.get("role"),
        allowed_pages=data.get("allowed_pages"),
    )
    if user is None:
        return jsonify({"error": "User not found or username conflict"}), 404

    return jsonify(user.to_safe_dict())


@main_bp.route("/api/admin/users/<user_id>", methods=["DELETE"])
@login_required
def api_delete_user(user_id):
    """Delete a user."""
    if current_user.role != "admin":
        return jsonify({"error": "Forbidden"}), 403

    success, message = delete_user(user_id)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message})


# ── New API routes (region-based reports) ──────────────────────────────
# Public endpoints (no login required) – mirrors existing public API pattern
@main_bp.route("/api/regions")
def api_regions():
    """Return list of available regions."""
    try:
        return jsonify(get_available_regions())
    except oracledb.Error:
        logger.exception("Failed to fetch regions")
        return jsonify({"error": "Database error: unable to fetch regions"}), 500


# Public endpoint – matches existing /api/integration-status pattern
@main_bp.route("/api/sales-integration-detail")
def api_sales_integration_detail():
    """Return SALES_INTEGRATION_STATUS detail."""
    try:
        return jsonify(get_sales_integration_detail())
    except oracledb.Error:
        logger.exception("Failed to fetch sales integration detail")
        return jsonify({"error": "Database error: unable to fetch sales integration detail"}), 500


@main_bp.route("/api/reports/invoice-headers")
@login_required
def api_invoice_headers():
    """Return invoice header data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_invoice_header_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch invoice headers")
        return jsonify({"error": "Database error: unable to fetch invoice headers"}), 500


@main_bp.route("/api/reports/invoice-lines")
@login_required
def api_invoice_lines():
    """Return invoice line data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_invoice_line_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch invoice lines")
        return jsonify({"error": "Database error: unable to fetch invoice lines"}), 500


@main_bp.route("/api/reports/misc-receipts")
@login_required
def api_misc_receipts():
    """Return misc receipt data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_misc_receipt_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch misc receipts")
        return jsonify({"error": "Database error: unable to fetch misc receipts"}), 500


@main_bp.route("/api/reports/standard-receipts")
@login_required
def api_standard_receipts():
    """Return standard receipt data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_standard_receipt_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch standard receipts")
        return jsonify({"error": "Database error: unable to fetch standard receipts"}), 500


@main_bp.route("/api/reports/apply-receipts")
@login_required
def api_apply_receipts():
    """Return apply receipt data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_apply_receipt_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch apply receipts")
        return jsonify({"error": "Database error: unable to fetch apply receipts"}), 500


@main_bp.route("/api/reports/inv-txn")
@login_required
def api_inv_txn():
    """Return inventory transaction data, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_fusion_inv_txn_report(region))
    except oracledb.Error:
        logger.exception("Failed to fetch inventory transactions")
        return jsonify({"error": "Database error: unable to fetch inventory transactions"}), 500


@main_bp.route("/api/reports/table-summary")
@login_required
def api_table_summary():
    """Return table status summary, optionally filtered by region."""
    try:
        region = request.args.get("region")
        return jsonify(get_table_status_summary(region))
    except oracledb.Error:
        logger.exception("Failed to fetch table summary")
        return jsonify({"error": "Database error: unable to fetch table summary"}), 500
