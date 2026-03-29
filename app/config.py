import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "odoo_integration")
    DB_USER = os.getenv("DB_USER", "odoo")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "30"))
