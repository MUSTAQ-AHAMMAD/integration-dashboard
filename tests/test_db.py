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
    yield
    db_module._app_config = None


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


# ── get_connection ─────────────────────────────────────────────────────
def test_get_connection_raises_if_not_initialised():
    """get_connection should raise RuntimeError when init_db was never called."""
    with pytest.raises(RuntimeError, match="Database not initialised"):
        db_module.get_connection()


@patch("app.db.oracledb.connect")
def test_get_connection_creates_standalone_connection(mock_connect):
    """get_connection should call oracledb.connect with the correct DSN."""
    _make_app()
    conn = db_module.get_connection()
    mock_connect.assert_called_once()
    kwargs = mock_connect.call_args[1]
    assert kwargs["dsn"] == "dbhost.example.com:1521/TESTDB"
    assert kwargs["user"] == "app_user"
    assert kwargs["password"] == "secret"
    assert conn is mock_connect.return_value


@patch("app.db.oracledb.connect")
def test_get_connection_sets_sysdba_mode(mock_connect):
    """get_connection should pass AUTH_MODE_SYSDBA when DB_MODE=SYSDBA."""
    _make_app(DB_MODE="SYSDBA")
    db_module.get_connection()
    kwargs = mock_connect.call_args[1]
    assert kwargs["mode"] == oracledb.AUTH_MODE_SYSDBA


@patch("app.db.oracledb.connect")
def test_get_connection_omits_mode_when_not_sysdba(mock_connect):
    """get_connection should not pass mode when DB_MODE is empty."""
    _make_app(DB_MODE="")
    db_module.get_connection()
    kwargs = mock_connect.call_args[1]
    assert "mode" not in kwargs


@patch("app.db.oracledb.connect", side_effect=oracledb.Error("connection refused"))
def test_get_connection_raises_on_failure(mock_connect):
    """get_connection should raise when oracledb.connect fails."""
    _make_app()
    with pytest.raises(oracledb.Error, match="connection refused"):
        db_module.get_connection()


@patch("app.db.time.sleep")
@patch("app.db.oracledb.connect")
def test_get_connection_retries_on_dpy4011(mock_connect, mock_sleep):
    """get_connection should retry on DPY-4011."""
    _make_app()
    dpy_err = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    good_conn = MagicMock()
    mock_connect.side_effect = [dpy_err, good_conn]

    conn = db_module.get_connection()
    assert conn is good_conn
    assert mock_connect.call_count == 2
    mock_sleep.assert_called_once_with(1)  # first retry: delay = 1 * (0+1) = 1


@patch("app.db.time.sleep")
@patch("app.db.oracledb.connect")
def test_get_connection_retries_multiple_times_on_dpy4011(mock_connect, mock_sleep):
    """get_connection should retry up to _MAX_RECONNECT_ATTEMPTS times."""
    _make_app()
    dpy_err = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    good_conn = MagicMock()
    mock_connect.side_effect = [dpy_err, dpy_err, good_conn]

    conn = db_module.get_connection()
    assert conn is good_conn
    assert mock_connect.call_count == 3
    # Linear backoff: attempt 0 → sleep(1), attempt 1 → sleep(2)
    assert mock_sleep.call_args_list == [call(1), call(2)]


@patch("app.db.time.sleep")
@patch("app.db.oracledb.connect")
def test_get_connection_raises_after_all_retries_exhausted(mock_connect, mock_sleep):
    """get_connection should raise DPY-4011 after all retries are exhausted."""
    _make_app()
    dpy_err = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    mock_connect.side_effect = dpy_err

    with pytest.raises(oracledb.Error, match="DPY-4011"):
        db_module.get_connection()
    # 1 initial + _MAX_RECONNECT_ATTEMPTS retries
    assert mock_connect.call_count == 1 + db_module._MAX_RECONNECT_ATTEMPTS
    assert mock_sleep.call_count == db_module._MAX_RECONNECT_ATTEMPTS
    # Linear backoff: 1, 2, 3
    expected = [
        call(db_module._RECONNECT_BASE_DELAY * (i + 1))
        for i in range(db_module._MAX_RECONNECT_ATTEMPTS)
    ]
    assert mock_sleep.call_args_list == expected


@patch("app.db.oracledb.connect")
def test_get_connection_raises_non_dpy4011_error(mock_connect):
    """get_connection should propagate non-DPY-4011 errors without retry."""
    _make_app()
    mock_connect.side_effect = oracledb.Error("ORA-12541: TNS:no listener")

    with pytest.raises(oracledb.Error, match="ORA-12541"):
        db_module.get_connection()
    # Only one attempt – no retry for non-DPY-4011 errors
    assert mock_connect.call_count == 1


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


@patch("app.db.get_connection")
def test_test_connection_retries_on_dpy4011(mock_conn_fn):
    """test_connection should retry once when the query raises DPY-4011."""
    # First connection: cursor.execute raises DPY-4011
    bad_cursor = MagicMock()
    bad_cursor.execute.side_effect = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    bad_conn = MagicMock()
    bad_conn.cursor.return_value = bad_cursor

    # Second connection (after retry): succeeds
    good_cursor = MagicMock()
    good_cursor.fetchone.return_value = (1,)
    good_conn = MagicMock()
    good_conn.cursor.return_value = good_cursor

    mock_conn_fn.side_effect = [bad_conn, good_conn]

    assert db_module.test_connection() is True
    bad_conn.close.assert_called_once()
    good_conn.close.assert_called_once()


@patch("app.db.get_connection")
def test_test_connection_no_retry_on_other_errors(mock_conn_fn):
    """test_connection should NOT retry on non-DPY-4011 query errors."""
    bad_cursor = MagicMock()
    bad_cursor.execute.side_effect = oracledb.Error("ORA-00942: table or view does not exist")
    bad_conn = MagicMock()
    bad_conn.cursor.return_value = bad_cursor
    mock_conn_fn.return_value = bad_conn

    with pytest.raises(oracledb.Error, match="ORA-00942"):
        db_module.test_connection()
    assert mock_conn_fn.call_count == 1


# ── _is_connection_closed_error ────────────────────────────────────────
def test_is_connection_closed_error_detects_dpy4011():
    """_is_connection_closed_error should return True for DPY-4011 messages."""
    exc = oracledb.Error("DPY-4011: the database or network closed the connection")
    assert db_module._is_connection_closed_error(exc) is True


def test_is_connection_closed_error_ignores_other_errors():
    """_is_connection_closed_error should return False for non-DPY-4011 errors."""
    exc = oracledb.Error("ORA-00942: table or view does not exist")
    assert db_module._is_connection_closed_error(exc) is False


# ── execute_query retry on DPY-4011 ───────────────────────────────────
@patch("app.db.get_connection")
def test_execute_query_retries_on_dpy4011(mock_conn_fn):
    """execute_query should retry the query once on DPY-4011."""
    # First connection: cursor.execute raises DPY-4011
    bad_cursor = MagicMock()
    bad_cursor.execute.side_effect = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    bad_conn = MagicMock()
    bad_conn.cursor.return_value = bad_cursor

    # Second connection (after retry): works normally
    good_cursor = MagicMock()
    good_cursor.description = [("ID",), ("NAME",)]
    good_cursor.fetchall.return_value = [(1, "Alice")]
    good_conn = MagicMock()
    good_conn.cursor.return_value = good_cursor

    mock_conn_fn.side_effect = [bad_conn, good_conn]

    rows = db_module.execute_query("SELECT id, name FROM users")

    assert rows == [{"id": 1, "name": "Alice"}]
    bad_conn.close.assert_called_once()
    good_conn.close.assert_called_once()


@patch("app.db.get_connection")
def test_execute_query_raises_on_retry_failure(mock_conn_fn):
    """execute_query should raise if the retry also fails."""
    bad_cursor = MagicMock()
    bad_cursor.execute.side_effect = oracledb.Error(
        "DPY-4011: the database or network closed the connection"
    )
    bad_conn1 = MagicMock()
    bad_conn1.cursor.return_value = bad_cursor

    bad_cursor2 = MagicMock()
    bad_cursor2.execute.side_effect = oracledb.Error("ORA-01034: ORACLE not available")
    bad_conn2 = MagicMock()
    bad_conn2.cursor.return_value = bad_cursor2

    mock_conn_fn.side_effect = [bad_conn1, bad_conn2]

    with pytest.raises(oracledb.Error, match="ORA-01034"):
        db_module.execute_query("SELECT 1 FROM DUAL")


@patch("app.db.get_connection")
def test_execute_query_no_retry_on_other_errors(mock_conn_fn):
    """execute_query should NOT retry on non-DPY-4011 errors."""
    bad_cursor = MagicMock()
    bad_cursor.execute.side_effect = oracledb.Error("ORA-00942: table or view does not exist")
    bad_conn = MagicMock()
    bad_conn.cursor.return_value = bad_cursor
    mock_conn_fn.return_value = bad_conn

    with pytest.raises(oracledb.Error, match="ORA-00942"):
        db_module.execute_query("SELECT * FROM missing_table")
    # Only one connection acquired – no retry
    assert mock_conn_fn.call_count == 1


# ── _validate_config ──────────────────────────────────────────────────
def test_validate_config_returns_empty_when_all_present():
    """_validate_config should return an empty list when all required keys are set."""
    app = _make_app()
    missing = db_module._validate_config(app)
    assert missing == []


def test_validate_config_detects_empty_db_user():
    """_validate_config should flag DB_USER when it is empty."""
    app = _make_app(DB_USER="")
    missing = db_module._validate_config(app)
    assert "DB_USER" in missing


def test_validate_config_detects_empty_db_password():
    """_validate_config should flag DB_PASSWORD when it is empty."""
    app = _make_app(DB_PASSWORD="")
    missing = db_module._validate_config(app)
    assert "DB_PASSWORD" in missing


def test_validate_config_detects_multiple_missing_keys():
    """_validate_config should flag all missing keys at once."""
    app = _make_app(DB_USER="", DB_PASSWORD="", DB_HOST="")
    missing = db_module._validate_config(app)
    assert "DB_USER" in missing
    assert "DB_PASSWORD" in missing
    assert "DB_HOST" in missing


# ── startup probe ─────────────────────────────────────────────────────
@patch("app.db.oracledb.connect")
def test_init_db_startup_probe_runs_when_not_testing(mock_connect):
    """init_db should attempt a connectivity probe when TESTING is not set."""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    cfg = {
        "SECRET_KEY": "test-secret",
        "DB_HOST": "dbhost.example.com",
        "DB_PORT": "1521",
        "DB_SERVICE_NAME": "TESTDB",
        "DB_USER": "app_user",
        "DB_PASSWORD": "secret",
        "DB_MODE": "",
        "REFRESH_INTERVAL": 10,
    }
    create_app(config=cfg)
    mock_connect.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("app.db.oracledb.connect")
def test_init_db_startup_probe_skipped_in_testing(mock_connect):
    """init_db should skip the connectivity probe in TESTING mode."""
    _make_app()  # TESTING=True by default in _make_app
    mock_connect.assert_not_called()


@patch("app.db.oracledb.connect", side_effect=oracledb.Error("DPY-4011: connection closed"))
def test_init_db_startup_probe_failure_does_not_raise(mock_connect):
    """init_db should log a warning but NOT raise on probe failure."""
    cfg = {
        "SECRET_KEY": "test-secret",
        "DB_HOST": "dbhost.example.com",
        "DB_PORT": "1521",
        "DB_SERVICE_NAME": "TESTDB",
        "DB_USER": "app_user",
        "DB_PASSWORD": "secret",
        "DB_MODE": "",
        "REFRESH_INTERVAL": 10,
    }
    # Should not raise – the probe is non-blocking
    app = create_app(config=cfg)
    assert app is not None


# ── DPY-4011 help URL in module constants ─────────────────────────────
def test_dpy4011_help_url_is_defined():
    """The module should expose the troubleshooting URL."""
    assert "troubleshooting" in db_module._DPY4011_HELP_URL
    assert "dpy-4011" in db_module._DPY4011_HELP_URL
