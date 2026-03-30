import os

from flask import Flask

from app.config import Config
from app.db import init_db
from app.oracle_client import init_oracle_client


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(config)

    # Initialise Oracle Thick mode before any database connections.
    init_oracle_client(app.config)

    init_db(app)

    from app.auth import init_auth
    init_auth(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
