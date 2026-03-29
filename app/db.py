import logging

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

_app_config = None


def init_db(app):
    """Store app config for later database connections."""
    global _app_config
    _app_config = {
        "host": app.config["DB_HOST"],
        "port": app.config["DB_PORT"],
        "dbname": app.config["DB_NAME"],
        "user": app.config["DB_USER"],
        "password": app.config["DB_PASSWORD"],
    }


def get_connection():
    """Create and return a new database connection."""
    if _app_config is None:
        raise RuntimeError("Database not initialised. Call init_db(app) first.")
    return psycopg2.connect(**_app_config)


def execute_query(query, params=None):
    """Execute a query and return all rows as a list of dicts."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.Error:
        logger.exception("Database query failed")
        return []
    finally:
        if conn is not None:
            conn.close()
