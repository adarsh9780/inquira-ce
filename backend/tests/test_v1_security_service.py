import hashlib

from app.v1.services.security_service import hash_password, verify_password


def test_hash_password_uses_pbkdf2_format_and_verifies():
    salt = "abc123salt"
    hashed = hash_password("secret123", salt)

    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("secret123", salt, hashed) is True
    assert verify_password("wrong", salt, hashed) is False


def test_verify_password_supports_legacy_sha256_hashes():
    salt = "legacy-salt"
    legacy_hash = hashlib.sha256(f"secret123{salt}".encode("utf-8")).hexdigest()

    assert verify_password("secret123", salt, legacy_hash) is True
    assert verify_password("wrong", salt, legacy_hash) is False
