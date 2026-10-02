"""Password hashing for local email authentication."""

import bcrypt

_MIN_PASSWORD_LEN = 8


def validate_password_strength(password: str) -> None:
    if len(password) < _MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {_MIN_PASSWORD_LEN} characters")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return digest.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
