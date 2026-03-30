import logging
import time

import oracledb

logger = logging.getLogger(__name__)

_app_config = None

# DPY-4011 is raised when the database or network closed the connection.
_CONNECTION_CLOSED_PREFIX = "DPY-4011"

# Retry settings for transient connection failures.  A fresh connection is
# attempted up to ``_MAX_RECONNECT_ATTEMPTS`` times with a linearly
# increasing delay.
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_BASE_DELAY = 1   # base delay in seconds (multiplied by attempt)


def _is_connection_closed_error(exc):
    """Return ``True`` if *exc* indicates a closed / dead connection (DPY-4011)."""
    return _CONNECTION_CLOSED_PREFIX in str(exc)


def init_db(app):
    """Store app config for on-demand connections.

    No persistent pool is created.  Each request opens a fresh connection
    and closes it when done.
    """
    global _app_config

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


def get_connection():
    """Create a new standalone connection to the database.

    If the attempt fails with a closed-connection error (DPY-4011)
    it is retried up to ``_MAX_RECONNECT_ATTEMPTS`` times with a
    linearly increasing delay.  The caller is responsible for closing
    the returned connection.
    """
    if _app_config is None:
        raise RuntimeError("Database not initialised. Call init_db(app) first.")

    kwargs = {
        "user": _app_config["user"],
        "password": _app_config["password"],
        "dsn": _dsn(),
    }
    if _app_config.get("mode", "").upper() == "SYSDBA":
        kwargs["mode"] = oracledb.AUTH_MODE_SYSDBA

    last_exc = None
    for attempt in range(1 + _MAX_RECONNECT_ATTEMPTS):
        try:
            conn = oracledb.connect(**kwargs)
            logger.debug("Opened connection to %s", _dsn_label())
            return conn
        except oracledb.Error as exc:
            if not _is_connection_closed_error(exc):
                logger.exception(
                    "Failed to connect to %s", _dsn_label()
                )
                raise
            last_exc = exc
            if attempt < _MAX_RECONNECT_ATTEMPTS:
                delay = _RECONNECT_BASE_DELAY * (attempt + 1)
                logger.warning(
                    "Connection failed (DPY-4011), retrying "
                    "(attempt %d/%d, backoff %ds)",
                    attempt + 1, _MAX_RECONNECT_ATTEMPTS, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "All %d reconnect attempts exhausted for %s",
                    _MAX_RECONNECT_ATTEMPTS, _dsn_label(),
                )
    raise last_exc  # pragma: no cover – only reachable when all retries fail


def _run_query(conn, query, params):
    """Execute *query* on *conn* and return rows as a list of dicts."""
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute_query(query, params=None):
    """Execute a query using a fresh connection that is closed afterwards.

    On a closed-connection error (DPY-4011) the query is retried once
    with a new connection.
    """
    conn = None
    try:
        conn = get_connection()
        return _run_query(conn, query, params)
    except oracledb.Error as exc:
        if _is_connection_closed_error(exc):
            logger.warning("Connection lost during query (DPY-4011), retrying once")
            if conn is not None:
                try:
                    conn.close()
                except oracledb.Error:
                    pass
                conn = None
            retry_conn = None
            try:
                retry_conn = get_connection()
                return _run_query(retry_conn, query, params)
            except oracledb.Error:
                logger.exception("Retry query also failed")
                raise
            finally:
                if retry_conn is not None:
                    retry_conn.close()
        else:
            logger.exception("Database query failed")
            raise
    finally:
        if conn is not None:
            conn.close()


def test_connection():
    """Verify connectivity by executing ``SELECT 1 FROM DUAL``.

    Returns ``True`` on success; raises on failure.
    If a DPY-4011 error occurs during the query a single retry is made
    with a new connection.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        return True
    except oracledb.Error as exc:
        if not _is_connection_closed_error(exc):
            raise
        logger.warning("Connection lost during health check (DPY-4011), retrying")
        if conn is not None:
            try:
                conn.close()
            except oracledb.Error:
                pass
            conn = None
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        return True
    finally:
        if conn is not None:
            conn.close()
