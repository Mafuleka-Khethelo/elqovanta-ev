"""Argon2id passwords and random login cookies.

The database stores a password hash and a SHA-256 hash of the session token.
The raw session token exists only in an HttpOnly cookie.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

SESSION_COOKIE = "cc_session"
CSRF_COOKIE = "cc_csrf"

# Argon2id is the PasswordHasher default. These parameters are a documented
# interactive-login cost, not a reduced test-only setting.
_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return _hasher.verify(encoded_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_verify(password: str) -> None:
    """Spend a similar amount of time when the email address is unknown."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("chargeconnect-timing-placeholder")
    verify_password(password, _dummy_hash)


def needs_rehash(encoded_hash: str) -> bool:
    return _hasher.check_needs_rehash(encoded_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(left: str | None, right: str | None) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def cookie_kwargs(settings: Settings, max_age: int) -> dict[str, object]:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "max_age": max_age,
        "path": "/",
    }
