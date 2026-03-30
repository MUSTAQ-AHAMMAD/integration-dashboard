import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Oracle connection settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "1521")
    DB_SERVICE_NAME = os.getenv("DB_SERVICE_NAME", "ORCL")
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_MODE = os.getenv("DB_MODE", "")

    # Oracle Instant Client path for Thick mode (needed for NNE / SYSDBA).
    # Leave empty to auto-detect via ORACLE_HOME or system search paths.
    ORACLE_CLIENT_PATH = os.getenv("ORACLE_CLIENT_PATH", "")

    REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "30"))
