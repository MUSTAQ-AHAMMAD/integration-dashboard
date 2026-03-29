import logging

import oracledb

logger = logging.getLogger(__name__)

_app_config = None


def init_db(app):
    """Store app config for later Oracle database connections."""
    global _app_config
    _app_config = {
        "host": app.config["DB_HOST"],
        "port": int(app.config["DB_PORT"]),
        "service_name": app.config["DB_SERVICE_NAME"],
        "user": app.config["DB_USER"],
        "password": app.config["DB_PASSWORD"],
        "mode": app.config.get("DB_MODE", ""),
    }


def get_connection():
    """Create and return a new Oracle database connection."""
    if _app_config is None:
        raise RuntimeError("Database not initialised. Call init_db(app) first.")
    dsn = oracledb.makedsn(
        _app_config["host"],
        _app_config["port"],
        service_name=_app_config["service_name"],
    )
    kwargs = {
        "user": _app_config["user"],
        "password": _app_config["password"],
        "dsn": dsn,
    }
    if _app_config.get("mode", "").upper() == "SYSDBA":
        kwargs["mode"] = oracledb.AUTH_MODE_SYSDBA
    return oracledb.connect(**kwargs)


def execute_query(query, params=None):
    """Execute a query and return all rows as a list of dicts."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except oracledb.Error:
        logger.exception("Database query failed")
        raise
    finally:
        if conn is not None:
            conn.close()
