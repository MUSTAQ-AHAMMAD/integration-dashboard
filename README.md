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

# 3. (Optional) Install Oracle Instant Client for Thick mode – see below
# 4. Configure the Oracle database connection
cp .env.example .env          # then edit .env with your Oracle credentials

# 5. Run the server
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

## Oracle Instant Client (Thick Mode)

If you connect as **SYS** with ``SYSDBA`` privileges, or your database
uses **Native Network Encryption (NNE)**, you need Oracle Thick mode.
Thick mode requires the Oracle Instant Client libraries.

### Installation

#### Linux (x64)

```bash
# Download from https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
sudo mkdir -p /opt/oracle
cd /opt/oracle
# Extract the Basic package (e.g. instantclient-basic-linux.x64-21.12.0.0.0dbru.zip)
sudo unzip instantclient-basic-linux.x64-*.zip
# Add to .env
echo "ORACLE_CLIENT_PATH=/opt/oracle/instantclient_21_12" >> .env
```

#### macOS (Intel / Apple Silicon)

```bash
# Download the DMG from https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html
# Mount the DMG and copy the libraries
mkdir -p ~/instantclient_21_12
cp /Volumes/instantclient-basic-macos.x64-21.12.0.0.0dbru/* ~/instantclient_21_12/
echo "ORACLE_CLIENT_PATH=$HOME/instantclient_21_12" >> .env
```

#### Windows

```powershell
# Download from https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
# Extract to C:\oracle\instantclient_21_12
# Add to .env
echo ORACLE_CLIENT_PATH=C:\oracle\instantclient_21_12 >> .env
```

After installation, set ``ORACLE_CLIENT_PATH`` in your ``.env`` file to
the directory containing the Oracle Client libraries.  The application
will automatically switch to Thick mode on startup.

## Troubleshooting DPY-4011

**Error:** ``DPY-4011: the database or network closed the connection``

This error occurs when the python-oracledb Thin driver cannot negotiate
the connection protocol with the Oracle server.  Common causes:

| Cause | Fix |
|---|---|
| Native Network Encryption (NNE) enabled on DB | Install Oracle Instant Client and enable Thick mode (see above) |
| Connecting as SYS with SYSDBA | Enable Thick mode **and** set ``DB_MODE=SYSDBA`` in ``.env`` |
| Network timeout / firewall | Check ``DB_HOST`` and ``DB_PORT``; ensure the Oracle listener is reachable |
| Idle connection terminated by server | The app retries automatically (up to 3 times) |

**Quick fix checklist:**

1. Install Oracle Instant Client (see above).
2. Set ``ORACLE_CLIENT_PATH`` in ``.env`` to the Instant Client directory.
3. Restart the application — logs will confirm "Oracle Thick mode enabled".
4. If the error persists, check ``ORACLE_HOME`` and ``TNS_ADMIN`` env vars.
5. See the [python-oracledb troubleshooting guide](https://python-oracledb.readthedocs.io/en/latest/user_guide/troubleshooting.html#dpy-4011).

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | Oracle database host |
| `DB_PORT` | `1521` | Oracle listener port |
| `DB_SERVICE_NAME` | `ORCL` | Oracle service name |
| `DB_USER` | `odoo_integration` | Oracle database user |
| `DB_PASSWORD` | *(empty)* | Oracle database password |
| `DB_MODE` | *(empty)* | Set to `SYSDBA` for SYS connections |
| `ORACLE_CLIENT_PATH` | *(empty)* | Path to Oracle Instant Client libraries (Thick mode) |
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
│   ├── oracle_client.py     # Oracle Thick mode initialisation
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