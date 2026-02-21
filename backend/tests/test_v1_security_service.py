from app.v1.services.security_service import hash_password


def test_hash_password_is_deterministic_for_same_input():
    salt = "abc123"
    password = "iamhappy"

    first = hash_password(password, salt)
    second = hash_password(password, salt)

    assert first == second
    assert len(first) == 64
