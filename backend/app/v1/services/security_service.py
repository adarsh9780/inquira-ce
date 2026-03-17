"""Security helpers for password hashing and session token generation."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from hmac import compare_digest

_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 390000
_PBKDF2_DIGEST_BYTES = 32


def generate_salt() -> str:
    """Generate a cryptographically secure salt string."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """Hash password with a salt using PBKDF2-SHA256."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
        dklen=_PBKDF2_DIGEST_BYTES,
    ).hex()
    return f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${digest}"


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """Verify a password hash, with backward-compatible legacy SHA-256 support."""
    candidate = str(stored_hash or "").strip()
    if not candidate:
        return False

    prefix = f"{_PBKDF2_ALGORITHM}$"
    if candidate.startswith(prefix):
        _, iterations_raw, digest = candidate.split("$", 2)
        try:
            iterations = int(iterations_raw)
        except ValueError:
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
            dklen=_PBKDF2_DIGEST_BYTES,
        ).hex()
        return compare_digest(expected, digest)

    # Backward compatibility for legacy unsafely-fast SHA-256 hashes.
    legacy_expected = hashlib.sha256(f"{password}{salt}".encode("utf-8")).hexdigest()
    return compare_digest(legacy_expected, candidate)


def generate_session_token() -> str:
    """Generate a unique session token for cookie authentication."""
    return str(uuid.uuid4())
