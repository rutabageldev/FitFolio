"""Docker secrets management for production deployments.

This module provides utilities to read sensitive configuration from Docker secrets
when running in production, while falling back to environment variables in development.
"""

import os
from pathlib import Path

# Sentinel value to distinguish "no default" from "default=None"
_UNSET = object()


def read_secret(secret_name: str, default: str | None | object = _UNSET) -> str | None:
    """
    Read a secret from Docker secrets or environment variables.

    In production (USE_DOCKER_SECRETS=true), reads from /run/secrets/{secret_name}.
    In development, falls back to environment variable.

    Args:
        secret_name: Name of the secret/environment variable
        default: Default value if secret is not found (can be None)

    Returns:
        Secret value as string, or None if default=None and secret not found

    Raises:
        RuntimeError: If secret is not found and no default provided
    """
    use_docker_secrets = os.getenv("USE_DOCKER_SECRETS", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if use_docker_secrets:
        secret_path = Path("/run/secrets") / secret_name
        if secret_path.exists():
            return secret_path.read_text().strip()

    # Fall back to environment variable
    env_value = os.getenv(secret_name.upper())
    if env_value:
        return env_value

    # Return default if provided (even if None)
    if default is not _UNSET:
        return default  # type: ignore

    raise RuntimeError(
        f"Secret '{secret_name}' not found in Docker secrets or environment variables"
    )


def get_database_url() -> str:
    """
    Construct DATABASE_URL from components, using Docker secrets for password.

    Returns:
        Complete PostgreSQL connection string

    Example:
        postgresql+psycopg://user:password@host:5432/dbname
    """
    # Read password from Docker secret or env
    postgres_password = read_secret("postgres_password")

    # Read other DB config from environment
    postgres_user = os.getenv("POSTGRES_USER", "fitfolio_user")
    postgres_host = os.getenv("POSTGRES_HOST", "db")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "fitfolio")

    return f"postgresql+psycopg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"


def get_smtp_username() -> str | None:
    """
    Read SMTP username from Docker secrets or environment.

    Returns:
        SMTP username, or None if not configured (for development)
    """
    return read_secret("smtp_username", default=None)


def get_smtp_password() -> str | None:
    """
    Read SMTP password from Docker secrets or environment.

    Returns:
        SMTP password, or None if not configured (for development)
    """
    return read_secret("smtp_password", default=None)
