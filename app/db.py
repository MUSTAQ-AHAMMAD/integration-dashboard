import logging

import oracledb

logger = logging.getLogger(__name__)

_app_config = None
_pool = None


def init_db(app):
    """Store app config and reset any existing pool.

    The connection pool is created lazily on first use so the application
    can start even when the database is temporarily unavailable.
    """
    global _app_config, _pool
    # Shut down a previous pool (e.g. when tests re-initialise the app)
    if _pool is not None:
        try:
            _pool.close(force=True)
        except oracledb.Error:
            pass
        _pool = None

    _app_config = {
        "host": app.config["DB_HOST"],
        "port": int(app.config["DB_PORT"]),
        "service_name": app.config["DB_SERVICE_NAME"],
        "user": app.config["DB_USER"],
        "password": app.config["DB_PASSWORD"],
        "mode": app.config.get("DB_MODE", ""),
    }


def _dsn():
    """Return an Easy Connect string: ``host:port/service_name``."""
    return (
        f"{_app_config['host']}:{_app_config['port']}"
        f"/{_app_config['service_name']}"
    )


def _dsn_label():
    """Human-readable connection target for log messages (no password)."""
    if _app_config is None:
        return "<not configured>"
    return f"{_app_config['user']}@{_dsn()}"


def _create_pool():
    """Create (or return the existing) connection pool – lazy init."""
    global _pool
    if _pool is not None:
        return _pool

    if _app_config is None:
        raise RuntimeError("Database not initialised. Call init_db(app) first.")

    kwargs = {
        "user": _app_config["user"],
        "password": _app_config["password"],
        "dsn": _dsn(),
        "min": 1,
        "max": 5,
        "increment": 1,
    }
    if _app_config.get("mode", "").upper() == "SYSDBA":
        kwargs["mode"] = oracledb.AUTH_MODE_SYSDBA

    try:
        _pool = oracledb.create_pool(**kwargs)
        logger.info("Connection pool created for %s", _dsn_label())
    except oracledb.Error:
        logger.exception("Failed to create connection pool for %s", _dsn_label())
        raise
    return _pool


def get_connection():
    """Acquire a connection from the pool."""
    pool = _create_pool()
    try:
        return pool.acquire()
    except oracledb.Error:
        logger.exception("Failed to acquire connection from pool for %s", _dsn_label())
        raise


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


def test_connection():
    """Verify connectivity by executing ``SELECT 1 FROM DUAL``.

    Returns ``True`` on success; raises on failure.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        return True
    finally:
        if conn is not None:
            conn.close()


def close_pool():
    """Shut down the connection pool (if any)."""
    global _pool
    if _pool is not None:
        try:
            _pool.close(force=True)
        except oracledb.Error:
            logger.exception("Error closing connection pool")
        finally:
            _pool = None
