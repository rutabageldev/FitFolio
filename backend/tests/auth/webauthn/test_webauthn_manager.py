from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_verify_registration_response_success(monkeypatch):
    import app.core.webauthn as wa

    # Fake verification object returned by library
    verification = SimpleNamespace(
        credential_id=b"\x01\x02",
        credential_public_key=b"pubkey",
        sign_count=7,
    )
    # Fake credential with nested response attributes
    credential = SimpleNamespace(
        response=SimpleNamespace(
            transports=["usb", "nfc"],
            authenticator_data=SimpleNamespace(backed_up=True, uv_available=False),
        )
    )

    monkeypatch.setattr(wa, "verify_registration_response", lambda **_: verification)

    mgr = wa.WebAuthnManager(
        rp_name="FitFolio", rp_id="localhost", origin="http://origin"
    )
    out = mgr.verify_registration_response(
        credential=credential,
        expected_rp_id="localhost",
        expected_origin="http://origin",
        expected_challenge=b"challenge-bytes",
        expected_user_id=None,
    )

    # Assert mapping
    assert out["credential_id"] == wa.bytes_to_base64url(b"\x01\x02")
    assert out["public_key"] == b"pubkey"
    assert out["sign_count"] == 7
    assert out["transports"] == ["usb", "nfc"]
    assert out["backed_up"] is True
    assert out["uv_available"] is False


@pytest.mark.asyncio
async def test_verify_registration_response_error(monkeypatch):
    import app.core.webauthn as wa

    def boom(**_):
        raise RuntimeError("reg-fail")

    monkeypatch.setattr(wa, "verify_registration_response", boom)

    mgr = wa.WebAuthnManager(
        rp_name="FitFolio", rp_id="localhost", origin="http://origin"
    )
    with pytest.raises(ValueError) as ei:
        mgr.verify_registration_response(
            credential=SimpleNamespace(
                response=SimpleNamespace(
                    authenticator_data=SimpleNamespace(), transports=[]
                )
            ),
            expected_rp_id="localhost",
            expected_origin="http://origin",
            expected_challenge=b"x",
        )
    assert "registration verification failed" in str(ei.value).lower()


@pytest.mark.asyncio
async def test_verify_authentication_response_success(monkeypatch):
    import app.core.webauthn as wa

    verification = SimpleNamespace(new_sign_count=42, user_verified=True)
    monkeypatch.setattr(wa, "verify_authentication_response", lambda **_: verification)

    mgr = wa.WebAuthnManager(
        rp_name="FitFolio", rp_id="localhost", origin="http://origin"
    )
    out = mgr.verify_authentication_response(
        credential={"id": "dummy"},
        expected_rp_id="localhost",
        expected_origin="http://origin",
        expected_challenge=b"c",
        credential_public_key=b"pk",
        credential_current_sign_count=1,
    )
    assert out == {"new_sign_count": 42, "user_verified": True}


@pytest.mark.asyncio
async def test_verify_authentication_response_error(monkeypatch):
    import app.core.webauthn as wa

    def boom(**_):
        raise RuntimeError("auth-fail")

    monkeypatch.setattr(wa, "verify_authentication_response", boom)

    mgr = wa.WebAuthnManager(
        rp_name="FitFolio", rp_id="localhost", origin="http://origin"
    )
    with pytest.raises(ValueError) as ei:
        mgr.verify_authentication_response(
            credential={"id": "dummy"},
            expected_rp_id="localhost",
            expected_origin="http://origin",
            expected_challenge=b"c",
            credential_public_key=b"pk",
            credential_current_sign_count=1,
        )
    assert "authentication verification failed" in str(ei.value).lower()
