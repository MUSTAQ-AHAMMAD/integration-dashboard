"""Run the dashboard with in-memory demo data (no database needed).

Usage:  python demo.py
Then open http://localhost:5000 in a browser.
"""

import datetime
import random
from unittest.mock import patch

REGIONS = ["SA", "AE", "KW", "OM", "BH", "QR"]
INTEGRATIONS = [
    "Invoice Header Sync", "Invoice Line Sync", "Misc Receipt Sync",
    "Standard Receipt Sync", "Apply Receipt Sync", "Inventory Txn Sync",
]
STATUSES = ["running", "running", "running", "stopped", "error"]

_demo_integration_status = []
for _region in REGIONS:
    for _integ in INTEGRATIONS:
        _status = random.choice(STATUSES)
        _err = None
        if _status == "error":
            _err = random.choice([
                "Connection timeout after 30s",
                "Authentication failed: invalid token",
                "Record lock conflict on fusion_invoice_header",
                "API rate limit exceeded (429)",
                "Disk space critically low on sync server",
            ])
        _demo_integration_status.append({
            "region": _region,
            "integration_name": _integ,
            "status": _status,
            "last_run_time": (datetime.datetime.now(datetime.timezone.utc)
                              - datetime.timedelta(minutes=random.randint(0, 120))).isoformat(),
            "error_message": _err,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

TABLE_NAMES = [
    "fusion_invoice_header", "fusion_invoice_line", "fusion_misc_receipt",
    "fusion_standard_receipt", "fusion_apply_receipt", "fusion_inv_txn",
]
_demo_table_errors = []
for _t in TABLE_NAMES:
    _counts = []
    for _st in ["success", "error", "pending"]:
        _counts.append({"status": _st, "count": random.randint(0, 500)})
    _demo_table_errors.append({"table": _t, "status_counts": _counts})


_demo_management_report = {
    "IBRAQ": [
        {
            "integration_type": "IBRAQ",
            "country": "KSA",
            "completed_date": "2026-02-11",
            "current_date": "2026-02-12",
            "is_running": "No",
            "reason": "Need to correct 2 & 5 ,6 Feb missing data. Waiting for data sync",
            "expected_date": "30-Apr",
        },
        {
            "integration_type": "IBRAQ",
            "country": "UAE",
            "completed_date": "2026-03-18",
            "current_date": "2026-03-19",
            "is_running": "NO",
            "reason": "Waiting for finance to fix negative",
            "expected_date": "31-Mar",
        },
        {
            "integration_type": "IBRAQ",
            "country": "OMAN",
            "completed_date": "2026-03-18",
            "current_date": "2026-03-19",
            "is_running": "No",
            "reason": "Waiting for finance to fix negative",
            "expected_date": "31-Mar",
        },
        {
            "integration_type": "IBRAQ",
            "country": "KWT",
            "completed_date": "2026-03-25",
            "current_date": "2026-03-26",
            "is_running": "No",
            "reason": "",
            "expected_date": "Up to Date",
        },
        {
            "integration_type": "IBRAQ",
            "country": "BH",
            "completed_date": "2026-03-20",
            "current_date": "2026-03-21",
            "is_running": "YES",
            "reason": "",
            "expected_date": "31-Mar",
        },
    ],
    "MATCH": [
        {
            "integration_type": "MATCH",
            "country": "KSA",
            "completed_date": "2026-03-14",
            "current_date": "2026-03-15",
            "is_running": "YES",
            "reason": "High volume of transaction processing. Done for 26 Mar also",
            "expected_date": "3-Apr",
        },
    ],
}

# Demo data for sales_integration_status detail
_demo_sales_integration_detail = []
for _region in REGIONS:
    for _mode in ["AUTOMATIC", "MANUAL"]:
        _st = random.choice(["RUNNING", "IDLE", "IDLE"])
        _demo_sales_integration_detail.append({
            "region": _region, "integ_mode": _mode, "status": _st,
        })

# Demo data for report tables
def _make_demo_rows(table_key, region=None):
    """Generate demo rows for report queries."""
    rows = []
    _regions = [region] if region else REGIONS
    for reg in _regions:
        for i in range(random.randint(3, 8)):
            base = {
                "row_id": random.randint(100000, 999999),
                "request_id": random.randint(30000, 35000),
                "status": random.choice(["Success", "Success", "Success", "Failed"]),
                "message": "" if random.random() > 0.3 else "Error: timeout",
                "request_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "region": reg,
            }
            if table_key == "invoice_header":
                base.update({
                    "bill_to_cust_name": random.choice(["Salam Mall", "Red Sea Mall", "SAMTAHMALL"]),
                    "bill_to_location": str(random.randint(1, 100)),
                    "business_unit": "AlQurashi-KSA",
                    "txn_source": "Vend",
                    "txn_type": "Vend Invoice",
                    "txn_date": "2026-03-29",
                    "gl_date": "2026-03-29",
                    "currency_code": "SAR",
                    "txn_number": str(random.randint(2800000, 2900000)),
                })
            elif table_key == "invoice_line":
                base.update({
                    "invoice_number": str(random.randint(2500000, 2600000)),
                    "line_number": i + 1,
                    "item_number": str(random.randint(6000000000000, 7000000000000)),
                    "description": random.choice(["DIAMOND COLLECTION-BLUE", "TOBACCO COLLECTION"]),
                    "quantity": random.randint(1, 10),
                    "unit_selling_price": round(random.uniform(50, 300), 2),
                    "currency_code": "SAR",
                })
            elif table_key == "misc_receipt":
                base.update({
                    "receipt_number": f"Mada-{random.randint(2500000, 2600000)}-MISC",
                    "receipt_method_name": random.choice(["Mada", "Visa", "Master"]),
                    "bank_acc_number": "AL Jazeerah Bank",
                    "amount": round(random.uniform(-100, -5), 2),
                    "currency_code": "SAR",
                    "gl_date": "2026-03-29",
                    "receipt_date": "2026-03-29",
                    "exchange_date": "2026-03-29",
                    "integ_mode": "AUTOMATIC",
                })
            elif table_key == "standard_receipt":
                base.update({
                    "receipt_number": f"Mada-{random.randint(2500000, 2600000)}",
                    "amount": round(random.uniform(100, 5000), 2),
                    "currency_code": "SAR",
                    "gl_date": "2026-03-29",
                    "receipt_date": "2026-03-29",
                    "exchange_date": "2026-03-29",
                    "integ_mode": "AUTOMATIC",
                })
            elif table_key == "apply_receipt":
                base.update({
                    "accounting_date": "2026-03-29",
                    "application_date": "2026-03-29",
                    "txn_number": str(random.randint(2800000, 2900000)),
                    "receipt_number": f"Cash-{random.randint(2800000, 2900000)}",
                    "amount_applied": random.randint(100, 10000),
                    "currency_code": "SAR",
                    "integ_mode": "MANUAL",
                })
            elif table_key == "inv_txn":
                base.update({
                    "organization_name": "Showrooms Stores",
                    "item_number": str(random.randint(6000000000000, 7000000000000)),
                    "txn_source_name": f"MAKABRAJ1/{random.randint(130000, 140000)}",
                    "sunbinventory": "MAKABRAJ1",
                    "txn_date": "2026-03-29",
                    "txn_qty": random.choice([-1, 1, -4, 2]),
                    "integ_mode": "MANUAL",
                })
            rows.append(base)
    return rows


def _kpis():
    total = len(_demo_integration_status)
    running = sum(1 for r in _demo_integration_status if r["status"] == "running")
    stopped = sum(1 for r in _demo_integration_status if r["status"] == "stopped")
    error = sum(1 for r in _demo_integration_status if r["status"] == "error")
    return {"total": total, "running": running, "stopped": stopped, "error": error}


def _region_summary():
    regions = {}
    for r in _demo_integration_status:
        reg = r["region"]
        if reg not in regions:
            regions[reg] = {"region": reg, "total": 0, "running": 0, "stopped": 0, "error": 0}
        regions[reg]["total"] += 1
        regions[reg][r["status"]] += 1
    return sorted(regions.values(), key=lambda x: x["region"])


# Monkey-patch the query functions so no database is needed
with patch("app.queries.get_integration_status", return_value=_demo_integration_status), \
     patch("app.queries.get_overall_kpis", side_effect=lambda: _kpis()), \
     patch("app.queries.get_region_summary", side_effect=lambda: _region_summary()), \
     patch("app.queries.get_table_error_summary", return_value=_demo_table_errors), \
     patch("app.queries.get_table_errors", return_value=[]), \
     patch("app.queries.get_management_report", return_value=_demo_management_report), \
     patch("app.queries.get_available_regions", return_value=REGIONS), \
     patch("app.queries.get_sales_integration_detail", return_value=_demo_sales_integration_detail), \
     patch("app.queries.get_fusion_invoice_header_report", side_effect=lambda r=None: _make_demo_rows("invoice_header", r)), \
     patch("app.queries.get_fusion_invoice_line_report", side_effect=lambda r=None: _make_demo_rows("invoice_line", r)), \
     patch("app.queries.get_fusion_misc_receipt_report", side_effect=lambda r=None: _make_demo_rows("misc_receipt", r)), \
     patch("app.queries.get_fusion_standard_receipt_report", side_effect=lambda r=None: _make_demo_rows("standard_receipt", r)), \
     patch("app.queries.get_fusion_apply_receipt_report", side_effect=lambda r=None: _make_demo_rows("apply_receipt", r)), \
     patch("app.queries.get_fusion_inv_txn_report", side_effect=lambda r=None: _make_demo_rows("inv_txn", r)), \
     patch("app.queries.get_table_status_summary", return_value=_demo_table_errors):

    from app import create_app

    app = create_app(config={
        "TESTING": True,
        "SECRET_KEY": "demo",
        "DB_HOST": "localhost",
        "DB_PORT": "1521",
        "DB_SERVICE_NAME": "ORCL",
        "DB_USER": "demo",
        "DB_PASSWORD": "demo",
        "REFRESH_INTERVAL": 15,
    })

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=False)
