# Odoo Integration Dashboard

Premium real-time analytics dashboard for monitoring Odoo integration pipelines
across multiple regions, powered by **Oracle Database**. Built with a dark-theme
command-center design for management visibility into running/stopped/error states
of all integration processes.

## Features

- **Animated KPI Cards** – total, running, stopped and error counts with glow effects
- **Overall Status Doughnut Chart** – sleek donut with gradient colours
- **Region-wise Stacked Bar Chart** – status per region (US, EU, APAC, …)
- **Oracle Table Status Summary** – per-table status counts for all six fusion tables
- **Integration Status Table** – detailed view with region, name, status badges,
  last run time, error message and last-updated timestamp
- **Dark-theme glassmorphism UI** – premium command-center aesthetic
- **Auto-refresh with live indicator** – configurable polling interval (default 30 s)

## Monitored Tables (Oracle)

| Table | Purpose |
|---|---|
| `odoo_integration.fusion_invoice_header` | Invoice headers |
| `odoo_integration.fusion_invoice_line` | Invoice lines |
| `odoo_integration.fusion_misc_receipt` | Miscellaneous receipts |
| `odoo_integration.fusion_standard_receipt` | Standard receipts |
| `odoo_integration.fusion_apply_receipt` | Applied receipts |
| `odoo_integration.fusion_inv_txn` | Inventory transactions |
| `odoo_integration.sales_integration_status` | Integration running status |

## Quick Start

```bash
# 1. Clone & enter the repo
git clone <repo-url> && cd integration-dashboard

# 2. Create a virtual environment & install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure the Oracle database connection
cp .env.example .env          # then edit .env with your Oracle credentials

# 4. Run the server
python run.py                 # development
# or
gunicorn run:app --bind 0.0.0.0:5000   # production
```

Open **http://localhost:5000** in your browser.

## Demo Mode (no database)

```bash
python demo.py
```

Starts the dashboard with randomly generated data so you can preview the UI
without an Oracle database connection.

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | Oracle database host |
| `DB_PORT` | `1521` | Oracle listener port |
| `DB_SERVICE_NAME` | `ORCL` | Oracle service name |
| `DB_USER` | `odoo_integration` | Oracle database user |
| `DB_PASSWORD` | *(empty)* | Oracle database password |
| `FLASK_SECRET_KEY` | `dev-secret-key` | Flask session secret |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `REFRESH_INTERVAL` | `30` | Dashboard auto-refresh interval (seconds) |

## Project Structure

```
integration-dashboard/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration from .env
│   ├── db.py                # Oracle database connection helpers
│   ├── queries.py           # Oracle SQL queries for each dashboard section
│   ├── routes.py            # Flask routes (page + JSON APIs)
│   ├── static/
│   │   ├── css/dashboard.css  # Premium dark-theme styles
│   │   └── js/dashboard.js   # Front-end fetch + Chart.js logic
│   └── templates/
│       ├── base.html
│       └── dashboard.html
├── tests/
│   ├── conftest.py
│   └── test_routes.py
├── demo.py                  # Demo server with mock data
├── run.py                   # Production entry point
├── requirements.txt
├── .env.example
└── README.md
```