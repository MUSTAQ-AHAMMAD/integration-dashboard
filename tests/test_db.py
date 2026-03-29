"""Tests for the database connection layer (app.db)."""

from unittest.mock import MagicMock, patch, call

import oracledb
import pytest

from app import create_app
from app import db as db_module


# ── Helpers ────────────────────────────────────────────────────────────
def _make_app(**overrides):
    """Return a Flask app with test DB config, optionally overridden."""
    cfg = {
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "DB_HOST": "dbhost.example.com",
        "DB_PORT": "1521",
        "DB_SERVICE_NAME": "TESTDB",
        "DB_USER": "app_user",
        "DB_PASSWORD": "secret",
        "DB_MODE": "",
        "REFRESH_INTERVAL": 10,
    }
    cfg.update(overrides)
    return create_app(config=cfg)


@pytest.fixture(autouse=True)
def _reset_db_state():
    """Ensure each test starts with a clean DB module state."""
    db_module._app_config = None
    db_module._pool = None
    yield
    db_module._app_config = None
    db_module._pool = None


# ── init_db ────────────────────────────────────────────────────────────
def test_init_db_stores_config():
    """init_db should store all connection parameters from app config."""
    app = _make_app()
    assert db_module._app_config is not None
    assert db_module._app_config["host"] == "dbhost.example.com"
    assert db_module._app_config["port"] == 1521
    assert db_module._app_config["service_name"] == "TESTDB"
    assert db_module._app_config["user"] == "app_user"
    assert db_module._app_config["password"] == "secret"


def test_init_db_converts_port_to_int():
    """init_db should convert the port string to an integer."""
    _make_app(DB_PORT="1522")
    assert db_module._app_config["port"] == 1522


def test_init_db_stores_sysdba_mode():
    """init_db should store DB_MODE for SYSDBA support."""
    _make_app(DB_MODE="SYSDBA")
    assert db_module._app_config["mode"] == "SYSDBA"


def test_init_db_resets_pool():
    """Calling init_db again should close and reset any existing pool."""
    mock_pool = MagicMock()
    db_module._pool = mock_pool
    _make_app()
    mock_pool.close.assert_called_once_with(force=True)
    assert db_module._pool is None


def test_init_db_ignores_pool_close_error():
    """init_db should not raise if closing the old pool fails."""
    mock_pool = MagicMock()
    mock_pool.close.side_effect = oracledb.Error("close failed")
    db_module._pool = mock_pool
    _make_app()  # should not raise
    assert db_module._pool is None


# ── _dsn / _dsn_label ─────────────────────────────────────────────────
def test_dsn_format():
    """_dsn should return an Easy Connect string."""
    _make_app()
    assert db_module._dsn() == "dbhost.example.com:1521/TESTDB"


def test_dsn_label_includes_user():
    """_dsn_label should include the username but not the password."""
    _make_app()
    label = db_module._dsn_label()
    assert "app_user@" in label
    assert "dbhost.example.com:1521/TESTDB" in label
    assert "secret" not in label


def test_dsn_label_before_init():
    """_dsn_label should return a placeholder before init_db is called."""
    assert db_module._dsn_label() == "<not configured>"


# ── _create_pool ───────────────────────────────────────────────────────
def test_create_pool_raises_if_not_initialised():
    """_create_pool should raise RuntimeError when init_db was never called."""
    with pytest.raises(RuntimeError, match="Database not initialised"):
        db_module._create_pool()


@patch("app.db.oracledb.create_pool")
def test_create_pool_uses_dsn(mock_create, ):
    """_create_pool should pass the Easy Connect DSN to oracledb.create_pool."""
    _make_app()
    db_module._pool = None  # force pool creation
    db_module._create_pool()
    mock_create.assert_called_once()
    kwargs = mock_create.call_args[1]
    assert kwargs["dsn"] == "dbhost.example.com:1521/TESTDB"
    assert kwargs["user"] == "app_user"
    assert kwargs["password"] == "secret"
    assert kwargs["min"] == 1
    assert kwargs["max"] == 5


@patch("app.db.oracledb.create_pool")
def test_create_pool_sets_sysdba_mode(mock_create):
    """_create_pool should pass AUTH_MODE_SYSDBA when DB_MODE=SYSDBA."""
    _make_app(DB_MODE="SYSDBA")
    db_module._pool = None
    db_module._create_pool()
    kwargs = mock_create.call_args[1]
    assert kwargs["mode"] == oracledb.AUTH_MODE_SYSDBA


@patch("app.db.oracledb.create_pool")
def test_create_pool_omits_mode_when_not_sysdba(mock_create):
    """_create_pool should not pass mode when DB_MODE is empty."""
    _make_app(DB_MODE="")
    db_module._pool = None
    db_module._create_pool()
    kwargs = mock_create.call_args[1]
    assert "mode" not in kwargs


@patch("app.db.oracledb.create_pool")
def test_create_pool_returns_existing(mock_create):
    """_create_pool should return the existing pool without creating a new one."""
    _make_app()
    sentinel = MagicMock()
    db_module._pool = sentinel
    result = db_module._create_pool()
    assert result is sentinel
    mock_create.assert_not_called()


@patch("app.db.oracledb.create_pool", side_effect=oracledb.Error("cannot connect"))
def test_create_pool_propagates_error(mock_create):
    """_create_pool should re-raise oracledb.Error and leave _pool as None."""
    _make_app()
    db_module._pool = None
    with pytest.raises(oracledb.Error, match="cannot connect"):
        db_module._create_pool()
    assert db_module._pool is None


# ── get_connection ─────────────────────────────────────────────────────
@patch("app.db._create_pool")
def test_get_connection_acquires_from_pool(mock_pool_fn):
    """get_connection should acquire a connection from the pool."""
    _make_app()
    mock_pool = MagicMock()
    mock_pool_fn.return_value = mock_pool
    conn = db_module.get_connection()
    mock_pool.acquire.assert_called_once()
    assert conn is mock_pool.acquire.return_value


@patch("app.db._create_pool")
def test_get_connection_raises_on_acquire_failure(mock_pool_fn):
    """get_connection should raise when pool.acquire fails."""
    _make_app()
    mock_pool = MagicMock()
    mock_pool.acquire.side_effect = oracledb.Error("pool exhausted")
    mock_pool_fn.return_value = mock_pool
    with pytest.raises(oracledb.Error, match="pool exhausted"):
        db_module.get_connection()


# ── execute_query ──────────────────────────────────────────────────────
@patch("app.db.get_connection")
def test_execute_query_returns_dicts(mock_conn_fn):
    """execute_query should return a list of dicts keyed by lowercase column names."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("ID",), ("NAME",)]
    mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn_fn.return_value = mock_conn

    rows = db_module.execute_query("SELECT id, name FROM users")
    assert rows == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    mock_conn.close.assert_called_once()


@patch("app.db.get_connection")
def test_execute_query_passes_params(mock_conn_fn):
    """execute_query should pass bind parameters to cursor.execute."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("CNT",)]
    mock_cursor.fetchall.return_value = [(42,)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn_fn.return_value = mock_conn

    params = {"limit": 10}
    db_module.execute_query("SELECT COUNT(*) AS cnt FROM t WHERE rownum <= :limit", params)
    mock_cursor.execute.assert_called_once_with(
        "SELECT COUNT(*) AS cnt FROM t WHERE rownum <= :limit", params
    )


@patch("app.db.get_connection")
def test_execute_query_closes_conn_on_error(mock_conn_fn):
    """execute_query should close the connection even when the query fails."""
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = oracledb.Error("ORA-00942")
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn_fn.return_value = mock_conn

    with pytest.raises(oracledb.Error):
        db_module.execute_query("SELECT * FROM missing_table")
    mock_conn.close.assert_called_once()


@patch("app.db.get_connection", side_effect=oracledb.Error("no connection"))
def test_execute_query_raises_when_no_connection(mock_conn_fn):
    """execute_query should propagate connection errors."""
    with pytest.raises(oracledb.Error, match="no connection"):
        db_module.execute_query("SELECT 1 FROM DUAL")


# ── test_connection ────────────────────────────────────────────────────
@patch("app.db.get_connection")
def test_test_connection_success(mock_conn_fn):
    """test_connection should return True after executing SELECT 1 FROM DUAL."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn_fn.return_value = mock_conn

    assert db_module.test_connection() is True
    mock_cursor.execute.assert_called_once_with("SELECT 1 FROM DUAL")
    mock_conn.close.assert_called_once()


@patch("app.db.get_connection", side_effect=oracledb.Error("unreachable"))
def test_test_connection_failure(mock_conn_fn):
    """test_connection should raise when the database is unreachable."""
    with pytest.raises(oracledb.Error, match="unreachable"):
        db_module.test_connection()


# ── close_pool ─────────────────────────────────────────────────────────
def test_close_pool_closes_and_resets():
    """close_pool should close the pool and reset _pool to None."""
    mock_pool = MagicMock()
    db_module._pool = mock_pool
    db_module.close_pool()
    mock_pool.close.assert_called_once_with(force=True)
    assert db_module._pool is None


def test_close_pool_noop_when_no_pool():
    """close_pool should be a no-op when there is no pool."""
    db_module._pool = None
    db_module.close_pool()  # should not raise
    assert db_module._pool is None


def test_close_pool_resets_even_on_error():
    """close_pool should reset _pool to None even if pool.close raises."""
    mock_pool = MagicMock()
    mock_pool.close.side_effect = oracledb.Error("close failed")
    db_module._pool = mock_pool
    db_module.close_pool()  # should not raise
    assert db_module._pool is None
