"""Oracle Instant Client initialisation for Thick mode.

When the database uses Native Network Encryption (NNE) or when
connecting as ``SYS`` with ``AUTH_MODE_SYSDBA``, the python-oracledb
*Thin* driver may raise **DPY-4011**.  Switching to Thick mode by
loading the Oracle Instant Client libraries resolves this.

Usage — call :func:`init_oracle_client` **once** before any
``oracledb.connect()`` call (typically in the application factory).

The client library path is resolved in this order:

1. ``ORACLE_CLIENT_PATH`` environment variable / app config value.
2. ``ORACLE_HOME/lib`` (Linux/macOS) or ``ORACLE_HOME`` (Windows).
3. System default (``None``) — lets *oracledb* search
   ``PATH`` / ``LD_LIBRARY_PATH`` / ``DYLD_LIBRARY_PATH``.
"""

import logging
import os
import platform
import sys

import oracledb

logger = logging.getLogger(__name__)

# Module-level flag so we never call init_oracle_client() twice.
_thick_mode_initialised = False


def _resolve_lib_dir(app_config=None):
    """Return the Oracle Client library directory or ``None``.

    Resolution order:
    1. ``ORACLE_CLIENT_PATH`` from *app_config* dict or env var.
    2. ``ORACLE_HOME`` env var (``/lib`` appended on non-Windows).
    3. ``None`` — fall back to system search paths.
    """
    # 1. Explicit config / env var
    client_path = None
    if app_config:
        client_path = app_config.get("ORACLE_CLIENT_PATH", "")
    if not client_path:
        client_path = os.environ.get("ORACLE_CLIENT_PATH", "")
    if client_path and os.path.isdir(client_path):
        return client_path

    # 2. ORACLE_HOME
    oracle_home = os.environ.get("ORACLE_HOME", "")
    if oracle_home:
        if platform.system() == "Windows":
            candidate = oracle_home
        else:
            candidate = os.path.join(oracle_home, "lib")
        if os.path.isdir(candidate):
            return candidate

    # 3. Fall back to None (system search paths)
    return None


def init_oracle_client(app_config=None):
    """Initialise the Oracle Instant Client (Thick mode).

    Parameters
    ----------
    app_config : dict or None
        Application configuration mapping (e.g. ``app.config``).
        If provided, ``ORACLE_CLIENT_PATH`` is read from it.

    Returns
    -------
    bool
        ``True`` if Thick mode was successfully enabled, ``False``
        if the initialisation was skipped or failed (Thin mode is
        used as a fallback).
    """
    global _thick_mode_initialised

    if _thick_mode_initialised:
        logger.debug("Oracle Thick mode already initialised — skipping.")
        return True

    lib_dir = _resolve_lib_dir(app_config)

    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
        _thick_mode_initialised = True
        logger.info(
            "Oracle Thick mode enabled (lib_dir=%s).",
            lib_dir or "<system default>",
        )
        return True
    except Exception as exc:
        # Common reasons: libraries not found, wrong architecture, or
        # Thick mode already active from a previous call in the same
        # process.  Fall back to Thin mode gracefully.
        logger.warning(
            "Could not enable Oracle Thick mode (lib_dir=%s): %s. "
            "Falling back to Thin mode.  If you encounter DPY-4011 "
            "errors, install Oracle Instant Client and set "
            "ORACLE_CLIENT_PATH in your .env file.",
            lib_dir or "<system default>",
            exc,
        )
        return False


def is_thick_mode():
    """Return ``True`` if Thick mode has been successfully initialised."""
    return _thick_mode_initialised
