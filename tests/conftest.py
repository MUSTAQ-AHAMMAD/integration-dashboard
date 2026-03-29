"""Shared fixtures for the test suite."""

import pytest

from app import create_app


@pytest.fixture()
def app():
    """Create a Flask app configured for testing."""
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass",
        "REFRESH_INTERVAL": 10,
    }
    return create_app(config=test_config)


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()
