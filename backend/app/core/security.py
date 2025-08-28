import hashlib
import secrets


def create_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    """Hash a token using SHA-256."""
    return hashlib.sha256(token.encode()).digest()


def verify_token_hash(token: str, token_hash: bytes) -> bool:
    """Verify a token against its hash."""
    return hash_token(token) == token_hash


def create_magic_link_token() -> str:
    """Generate a secure random magic link token."""
    return secrets.token_urlsafe(32)


def hash_magic_link_token(token: str) -> bytes:
    """Hash a magic link token using SHA-256."""
    return hashlib.sha256(token.encode()).digest()
