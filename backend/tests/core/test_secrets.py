import sys
from pathlib import Path as RealPath

import pytest


def _patch_secrets_base(monkeypatch, tmp_path):
    """Redirect app.core.secrets.Path('/run/secrets') to tmp_path."""
    from app.core import secrets as secrets_mod

    def fake_path(p: str):
        if str(p) == "/run/secrets":
            return tmp_path
        return RealPath(p)

    monkeypatch.setattr(secrets_mod, "Path", fake_path, raising=True)
    return secrets_mod


def test_read_secret_file_present(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_DOCKER_SECRETS", "true")
    secrets_mod = _patch_secrets_base(monkeypatch, tmp_path)
    (tmp_path / "postgres_password").write_text("pw123\n")

    assert secrets_mod.read_secret("postgres_password") == "pw123"


def test_read_secret_env_fallback(monkeypatch):
    monkeypatch.delenv("USE_DOCKER_SECRETS", raising=False)
    monkeypatch.setenv("SMTP_PASSWORD", "envpw")

    from app.core.secrets import read_secret

    assert read_secret("smtp_password") == "envpw"


def test_missing_secret_raises_when_no_default(monkeypatch):
    monkeypatch.delenv("USE_DOCKER_SECRETS", raising=False)
    monkeypatch.delenv("NONEXISTENT", raising=False)

    from app.core.secrets import read_secret

    with pytest.raises(RuntimeError):
        read_secret("nonexistent")


def test_get_database_url_uses_secret_password(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_DOCKER_SECRETS", "true")
    monkeypatch.setenv("POSTGRES_USER", "theuser")
    monkeypatch.setenv("POSTGRES_HOST", "thehost")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DB", "thedb")

    secrets_mod = _patch_secrets_base(monkeypatch, tmp_path)
    (tmp_path / "postgres_password").write_text("superpw")

    assert (
        secrets_mod.get_database_url()
        == "postgresql+psycopg://theuser:superpw@thehost:6543/thedb"
    )


def test_get_smtp_username_and_password_optional(monkeypatch, tmp_path):
    # No secrets, no env -> None
    monkeypatch.setenv("USE_DOCKER_SECRETS", "true")
    secrets_mod = _patch_secrets_base(monkeypatch, tmp_path)

    assert secrets_mod.get_smtp_username() is None
    assert secrets_mod.get_smtp_password() is None

    # Env fallback
    monkeypatch.delenv("USE_DOCKER_SECRETS", raising=False)
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "ppppp")

    from app.core.secrets import get_smtp_password, get_smtp_username

    assert get_smtp_username() == "user@example.com"
    assert get_smtp_password() == "ppppp"


def test_integration_import_app_with_docker_secrets_enabled(monkeypatch, tmp_path):
    """
    Optional smoke: setting USE_DOCKER_SECRETS=true and providing secrets should
    not cause import-time errors when the app reads secrets for DB URL construction.
    """
    monkeypatch.setenv("USE_DOCKER_SECRETS", "true")
    # Ensure we don't accidentally use TEST_DATABASE_URL shortcut
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    # Provide the required DB secret
    (tmp_path / "postgres_password").write_text("pw-from-secret")
    _patch_secrets_base(monkeypatch, tmp_path)

    # Force fresh imports
    for mod in ["app.db.database", "app.main"]:
        if mod in sys.modules:
            del sys.modules[mod]

    # Import main app - should not raise
    import app.main  # noqa: F401
