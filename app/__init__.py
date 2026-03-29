import os

from flask import Flask

from app.config import Config
from app.db import init_db


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(config)

    init_db(app)

    from app.auth import init_auth
    init_auth(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
