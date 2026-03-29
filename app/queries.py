"""Data-access helpers that query the Odoo integration Oracle tables."""

import logging

from app.db import execute_query

logger = logging.getLogger(__name__)

# ── Tables whose error / status columns we read ────────────────────────
INTEGRATION_TABLES = [
    "odoo_integration.fusion_invoice_header",
    "odoo_integration.fusion_invoice_line",
    "odoo_integration.fusion_misc_receipt",
    "odoo_integration.fusion_standard_receipt",
    "odoo_integration.fusion_apply_receipt",
    "odoo_integration.fusion_inv_txn",
]


# ── Integration running status ─────────────────────────────────────────
def get_integration_status():
    """Return rows from the sales_integration_status table."""
    query = """
        SELECT region, integration_name, status, last_run_time,
               error_message, updated_at
        FROM odoo_integration.sales_integration_status
        ORDER BY region, integration_name
    """
    return execute_query(query)


# ── Error / status summary per table ───────────────────────────────────
def get_table_error_summary():
    """Return error and status counts for every monitored table."""
    results = []
    for table in INTEGRATION_TABLES:
        short_name = table.split(".")[-1]
        query = f"""
            SELECT status, COUNT(*) AS count
            FROM {table}
            GROUP BY status
            ORDER BY status
        """  # noqa: S608 – table names are from a fixed allow-list
        rows = execute_query(query)
        results.append({"table": short_name, "status_counts": rows})
    return results


def get_table_errors(table_short_name, limit=100):
    """Return the most recent error rows for a single table."""
    full_name = None
    for t in INTEGRATION_TABLES:
        if t.endswith(f".{table_short_name}"):
            full_name = t
            break
    if full_name is None:
        return []

    query = f"""
        SELECT *
        FROM {full_name}
        WHERE LOWER(status) IN ('error', 'failed', 'failure')
        ORDER BY created_at DESC
        FETCH FIRST :row_limit ROWS ONLY
    """  # noqa: S608
    return execute_query(query, {"row_limit": limit})


# ── Region-wise aggregation ────────────────────────────────────────────
def get_region_summary():
    """Aggregate integration status counts grouped by region."""
    query = """
        SELECT region,
               COUNT(*) AS total,
               SUM(CASE WHEN LOWER(status) = 'running' THEN 1 ELSE 0 END)  AS running,
               SUM(CASE WHEN LOWER(status) = 'stopped' THEN 1 ELSE 0 END)  AS stopped,
               SUM(CASE WHEN LOWER(status) = 'error'   THEN 1 ELSE 0 END)  AS error
        FROM odoo_integration.sales_integration_status
        GROUP BY region
        ORDER BY region
    """
    return execute_query(query)


# ── Management Report ──────────────────────────────────────────────────
def get_management_report():
    """Return management report rows grouped by integration type.

    Each row contains country-level progress for a given integration type
    (e.g. IBRAQ, MATCH).
    """
    query = """
        SELECT integration_type, country, completed_date, current_date,
               is_running, reason, expected_date
        FROM odoo_integration.integration_report
        ORDER BY integration_type, country
    """
    rows = execute_query(query)
    grouped = {}
    for row in rows:
        itype = row.get("integration_type", "UNKNOWN")
        grouped.setdefault(itype, []).append(row)
    return grouped


# ── Overall KPIs ───────────────────────────────────────────────────────
def get_overall_kpis():
    """Return high-level KPI numbers for the dashboard header."""
    status_rows = execute_query("""
        SELECT LOWER(status) AS status, COUNT(*) AS count
        FROM odoo_integration.sales_integration_status
        GROUP BY LOWER(status)
    """)
    kpis = {"total": 0, "running": 0, "stopped": 0, "error": 0}
    for row in status_rows:
        kpis["total"] += row["count"]
        st = row["status"]
        if st in kpis:
            kpis[st] = row["count"]
    return kpis


# ── Available regions ──────────────────────────────────────────────────
def get_available_regions():
    """Return distinct regions from sales_integration_status."""
    query = """
        SELECT DISTINCT region
        FROM odoo_integration.sales_integration_status
        ORDER BY region
    """
    rows = execute_query(query)
    return [r["region"] for r in rows]


# ── Sales integration detail ──────────────────────────────────────────
def get_sales_integration_detail():
    """Return SALES_INTEGRATION_STATUS with REGION, INTEG_MODE, STATUS."""
    query = """
        SELECT region, integ_mode, status
        FROM odoo_integration.sales_integration_status
        ORDER BY region, integ_mode
    """
    return execute_query(query)


# ── Report queries (region-filtered) ──────────────────────────────────
def get_fusion_invoice_line_report(region=None):
    """Query FUSION_INVOICE_LINE: status, message, request_date, invoice_number (latest)."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               invoice_number, line_number, item_number, description,
               quantity, unit_selling_price, currency_code, region
        FROM odoo_integration.fusion_invoice_line
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_fusion_misc_receipt_report(region=None):
    """Query FUSION_MISC_RECEIPT: status, message, request_date, gl_date, receipt_date, exchange_date."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               receipt_number, receipt_method_name, bank_acc_number,
               amount, currency_code, gl_date, receipt_date, exchange_date, region, integ_mode
        FROM odoo_integration.fusion_misc_receipt
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_fusion_standard_receipt_report(region=None):
    """Query FUSION_STANDARD_RECEIPT: status, message, request_date, gl_date, receipt_date, exchange_date."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               receipt_number, amount, currency_code,
               gl_date, receipt_date, exchange_date, region, integ_mode
        FROM odoo_integration.fusion_standard_receipt
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_fusion_apply_receipt_report(region=None):
    """Query FUSION_APPLY_RECEIPT: status, message, request_date, txn_number, receipt_number."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               accounting_date, application_date, txn_number, receipt_number,
               amount_applied, currency_code, region, integ_mode
        FROM odoo_integration.fusion_apply_receipt
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_fusion_inv_txn_report(region=None):
    """Query FUSION_INV_TXN: status, message, request_date, txn_source_name, sunbinventory, txn_date."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               organization_name, item_number, txn_source_name,
               sunbinventory, txn_date, txn_qty, region, integ_mode
        FROM odoo_integration.fusion_inv_txn
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_fusion_invoice_header_report(region=None):
    """Query FUSION_INVOICE_HEADER: status, message, request_date, bill_to details, txn details."""
    where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
    params = {"region": region} if region else {}
    query = f"""
        SELECT row_id, request_id, status, message, request_date,
               bill_to_cust_name, bill_to_location, business_unit,
               txn_source, txn_type, txn_date, gl_date,
               currency_code, txn_number, region
        FROM odoo_integration.fusion_invoice_header
        {where}
        ORDER BY row_id DESC
        FETCH FIRST 200 ROWS ONLY
    """
    return execute_query(query, params if params else None)


def get_table_status_summary(region=None):
    """Return success/failed counts per table, optionally filtered by region."""
    results = []
    for table in INTEGRATION_TABLES:
        short_name = table.split(".")[-1]
        where = "WHERE LOWER(region) = LOWER(:region)" if region else ""
        params = {"region": region} if region else {}
        query = f"""
            SELECT status, COUNT(*) AS count
            FROM {table}
            {where}
            GROUP BY status
            ORDER BY status
        """  # noqa: S608
        rows = execute_query(query, params if params else None)
        results.append({"table": short_name, "status_counts": rows})
    return results
