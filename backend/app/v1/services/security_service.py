"""Security helpers for password hashing and session token generation."""

from __future__ import annotations

import hashlib
import secrets
import uuid


def generate_salt() -> str:
    """Generate a cryptographically secure salt string."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """Hash password with a salt using SHA-256."""
    return hashlib.sha256(f"{password}{salt}".encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    """Generate a unique session token for cookie authentication."""
    return str(uuid.uuid4())
