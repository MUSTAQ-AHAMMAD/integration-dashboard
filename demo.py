"""Run the dashboard with in-memory demo data (no database needed).

Usage:  python demo.py
Then open http://localhost:5000 in a browser.
"""

import datetime
import random
from unittest.mock import patch

REGIONS = ["US", "EU", "APAC", "LATAM", "MEA"]
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
     patch("app.queries.get_table_errors", return_value=[]):

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
