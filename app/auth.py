"""User management module with JSON file storage and Flask-Login integration."""

import json
import logging
import os
import uuid

from flask_login import LoginManager, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

_users_file = None


class User(UserMixin):
    """Flask-Login compatible user model."""

    def __init__(self, id, username, password_hash, role, allowed_pages):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.allowed_pages = allowed_pages

    def to_dict(self):
        """Serialize user to a dictionary (includes password_hash for storage)."""
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "allowed_pages": self.allowed_pages,
        }

    def to_safe_dict(self):
        """Serialize user without password hash (for API responses)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "allowed_pages": self.allowed_pages,
        }


def init_auth(app):
    """Initialize Flask-Login and create default admin if no users exist."""
    global _users_file

    os.makedirs(app.instance_path, exist_ok=True)
    _users_file = os.path.join(app.instance_path, "users.json")

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "dev-secret-key"

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id):
        users = load_users()
        for u in users:
            if u["id"] == user_id:
                return User(**u)
        return None

    # Create default admin if no users exist
    users = load_users()
    if not users:
        create_user("admin", "admin123", "admin",
                     ["dashboard", "integration_report", "transaction_report"])
        logger.info("Created default admin user")


def load_users():
    """Read users from the JSON file."""
    if _users_file is None or not os.path.exists(_users_file):
        return []
    try:
        with open(_users_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Corrupted users.json file, returning empty user list")
        return []


def save_users(users):
    """Write users to the JSON file."""
    with open(_users_file, "w") as f:
        json.dump(users, f, indent=2)


def create_user(username, password, role="viewer", allowed_pages=None):
    """Create a new user and persist to JSON storage."""
    if allowed_pages is None:
        allowed_pages = ["dashboard"]

    users = load_users()

    # Check for duplicate username
    for u in users:
        if u["username"] == username:
            return None

    user_data = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "allowed_pages": allowed_pages,
    }
    users.append(user_data)
    save_users(users)
    return User(**user_data)


def delete_user(user_id):
    """Delete a user by ID. Cannot delete the last admin."""
    users = load_users()

    target = None
    for u in users:
        if u["id"] == user_id:
            target = u
            break

    if target is None:
        return False, "User not found"

    # Prevent deleting the last admin
    if target["role"] == "admin":
        admin_count = sum(1 for u in users if u["role"] == "admin")
        if admin_count <= 1:
            return False, "Cannot delete the last admin user"

    users = [u for u in users if u["id"] != user_id]
    save_users(users)
    return True, "User deleted"


def update_user(user_id, username=None, password=None, role=None,
                allowed_pages=None):
    """Update user details."""
    users = load_users()

    target = None
    for u in users:
        if u["id"] == user_id:
            target = u
            break

    if target is None:
        return None

    if username is not None:
        # Check for duplicate username
        for u in users:
            if u["username"] == username and u["id"] != user_id:
                return None
        target["username"] = username

    if password is not None:
        target["password_hash"] = generate_password_hash(password)

    if role is not None:
        target["role"] = role

    if allowed_pages is not None:
        target["allowed_pages"] = allowed_pages

    save_users(users)
    return User(**target)


def authenticate(username, password):
    """Verify credentials and return User object or None."""
    users = load_users()
    for u in users:
        if u["username"] == username:
            if check_password_hash(u["password_hash"], password):
                return User(**u)
            return None
    return None
