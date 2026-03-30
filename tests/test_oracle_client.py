"""Tests for Oracle Thick mode client initialisation (app.oracle_client)."""

from unittest.mock import patch

import pytest

from app import oracle_client as oc_module


@pytest.fixture(autouse=True)
def _reset_thick_mode():
    """Ensure each test starts with a clean module state."""
    oc_module._thick_mode_initialised = False
    yield
    oc_module._thick_mode_initialised = False


# ── _resolve_lib_dir ──────────────────────────────────────────────────

class TestResolveLibDir:
    """Tests for library directory resolution logic."""

    def test_returns_none_when_nothing_configured(self, tmp_path):
        """Should return None when no paths are configured."""
        with patch.dict("os.environ", {}, clear=True):
            assert oc_module._resolve_lib_dir() is None

    def test_uses_app_config_oracle_client_path(self, tmp_path):
        """Should prefer ORACLE_CLIENT_PATH from app config."""
        lib = tmp_path / "client"
        lib.mkdir()
        result = oc_module._resolve_lib_dir({"ORACLE_CLIENT_PATH": str(lib)})
        assert result == str(lib)

    def test_uses_env_oracle_client_path(self, tmp_path):
        """Should fall back to ORACLE_CLIENT_PATH env var."""
        lib = tmp_path / "client"
        lib.mkdir()
        with patch.dict("os.environ", {"ORACLE_CLIENT_PATH": str(lib)}):
            result = oc_module._resolve_lib_dir()
            assert result == str(lib)

    def test_app_config_takes_precedence_over_env(self, tmp_path):
        """App config ORACLE_CLIENT_PATH should win over the env var."""
        cfg_dir = tmp_path / "from_config"
        cfg_dir.mkdir()
        env_dir = tmp_path / "from_env"
        env_dir.mkdir()
        with patch.dict("os.environ", {"ORACLE_CLIENT_PATH": str(env_dir)}):
            result = oc_module._resolve_lib_dir(
                {"ORACLE_CLIENT_PATH": str(cfg_dir)}
            )
            assert result == str(cfg_dir)

    def test_skips_nonexistent_oracle_client_path(self, tmp_path):
        """Should skip ORACLE_CLIENT_PATH when directory doesn't exist."""
        result = oc_module._resolve_lib_dir(
            {"ORACLE_CLIENT_PATH": "/no/such/dir"}
        )
        assert result is None

    @patch("app.oracle_client.platform.system", return_value="Linux")
    def test_uses_oracle_home_lib_on_linux(self, _mock_sys, tmp_path):
        """Should append /lib to ORACLE_HOME on Linux."""
        home = tmp_path / "oracle_home"
        (home / "lib").mkdir(parents=True)
        with patch.dict("os.environ", {"ORACLE_HOME": str(home)}, clear=True):
            result = oc_module._resolve_lib_dir()
            assert result == str(home / "lib")

    @patch("app.oracle_client.platform.system", return_value="Windows")
    def test_uses_oracle_home_directly_on_windows(self, _mock_sys, tmp_path):
        """Should use ORACLE_HOME directly on Windows."""
        home = tmp_path / "oracle_home"
        home.mkdir()
        with patch.dict("os.environ", {"ORACLE_HOME": str(home)}, clear=True):
            result = oc_module._resolve_lib_dir()
            assert result == str(home)


# ── init_oracle_client ────────────────────────────────────────────────

class TestInitOracleClient:
    """Tests for the init_oracle_client function."""

    @patch("app.oracle_client.oracledb.init_oracle_client")
    @patch("app.oracle_client._resolve_lib_dir", return_value=None)
    def test_calls_init_oracle_client_with_resolved_path(
        self, mock_resolve, mock_init
    ):
        """Should call oracledb.init_oracle_client with the resolved dir."""
        result = oc_module.init_oracle_client({"ORACLE_CLIENT_PATH": ""})
        mock_init.assert_called_once_with(lib_dir=None)
        assert result is True

    @patch("app.oracle_client.oracledb.init_oracle_client")
    @patch("app.oracle_client._resolve_lib_dir", return_value="/opt/oracle/lib")
    def test_passes_lib_dir_when_resolved(self, mock_resolve, mock_init):
        """Should pass the resolved lib_dir to oracledb."""
        result = oc_module.init_oracle_client()
        mock_init.assert_called_once_with(lib_dir="/opt/oracle/lib")
        assert result is True

    @patch("app.oracle_client.oracledb.init_oracle_client")
    def test_sets_thick_mode_flag(self, mock_init):
        """Should set _thick_mode_initialised to True on success."""
        oc_module.init_oracle_client()
        assert oc_module._thick_mode_initialised is True

    @patch("app.oracle_client.oracledb.init_oracle_client")
    def test_skips_if_already_initialised(self, mock_init):
        """Should skip reinitialisation if Thick mode is already active."""
        oc_module._thick_mode_initialised = True
        result = oc_module.init_oracle_client()
        mock_init.assert_not_called()
        assert result is True

    @patch(
        "app.oracle_client.oracledb.init_oracle_client",
        side_effect=Exception("libs not found"),
    )
    def test_returns_false_on_failure(self, mock_init):
        """Should return False and not set flag when init fails."""
        result = oc_module.init_oracle_client()
        assert result is False
        assert oc_module._thick_mode_initialised is False

    @patch(
        "app.oracle_client.oracledb.init_oracle_client",
        side_effect=Exception("libs not found"),
    )
    def test_logs_warning_on_failure(self, mock_init, caplog):
        """Should log a warning with setup instructions on failure."""
        import logging

        with caplog.at_level(logging.WARNING):
            oc_module.init_oracle_client()
        assert "Falling back to Thin mode" in caplog.text


# ── is_thick_mode ─────────────────────────────────────────────────────

class TestIsThickMode:
    """Tests for the is_thick_mode helper."""

    def test_false_by_default(self):
        assert oc_module.is_thick_mode() is False

    @patch("app.oracle_client.oracledb.init_oracle_client")
    def test_true_after_successful_init(self, mock_init):
        oc_module.init_oracle_client()
        assert oc_module.is_thick_mode() is True
