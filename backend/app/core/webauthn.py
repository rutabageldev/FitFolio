import secrets
from typing import Any

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    COSEAlgorithmIdentifier,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    PublicKeyCredentialType,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)


class WebAuthnManager:
    """Manages WebAuthn operations for passkey authentication."""

    def __init__(self, rp_name: str, rp_id: str, origin: str):
        self.rp_name = rp_name
        self.rp_id = rp_id
        self.origin = origin

    def generate_registration_options(
        self,
        user_id: str,
        user_name: str,
        user_display_name: str,
        exclude_credentials: list[dict[str, Any]] | None = None,
    ) -> PublicKeyCredentialCreationOptions:
        """Generate WebAuthn registration options."""

        # Convert user_id string to bytes
        user_id_bytes = user_id.encode("utf-8")

        # Convert exclude_credentials to proper format if provided
        exclude_creds = []
        if exclude_credentials:
            for cred in exclude_credentials:
                exclude_creds.append(
                    PublicKeyCredentialDescriptor(
                        id=base64url_to_bytes(cred["id"]),
                        type=PublicKeyCredentialType.PUBLIC_KEY,
                        transports=[
                            AuthenticatorTransport(transport)
                            for transport in cred.get("transports", [])
                        ]
                        if cred.get("transports")
                        else None,
                    )
                )

        options = generate_registration_options(
            rp_name=self.rp_name,
            rp_id=self.rp_id,
            user_id=user_id_bytes,
            user_name=user_name,
            user_display_name=user_display_name,
            challenge=secrets.token_bytes(32),
            exclude_credentials=exclude_creds,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )

        return options

    def generate_authentication_options(
        self,
        allow_credentials: list[dict[str, Any]] | None = None,
    ) -> PublicKeyCredentialRequestOptions:
        """Generate WebAuthn authentication options."""

        # Convert allow_credentials to proper format if provided
        allow_creds = []
        if allow_credentials:
            for cred in allow_credentials:
                allow_creds.append(
                    PublicKeyCredentialDescriptor(
                        id=base64url_to_bytes(cred["id"]),
                        type=PublicKeyCredentialType.PUBLIC_KEY,
                        transports=[
                            AuthenticatorTransport(transport)
                            for transport in cred.get("transports", [])
                        ]
                        if cred.get("transports")
                        else None,
                    )
                )

        options = generate_authentication_options(
            rp_id=self.rp_id,
            challenge=secrets.token_bytes(32),
            allow_credentials=allow_creds,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        return options

    def verify_registration_response(
        self,
        credential: Any,  # RegistrationCredential or dict from JSON
        expected_rp_id: str,
        expected_origin: str,
        expected_challenge: bytes,
        expected_user_id: str | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Verify WebAuthn registration response."""

        try:
            # Note: webauthn library v2.x doesn't use expected_user_id
            # in verify_registration_response
            # User verification happens via the credential response itself
            verification = verify_registration_response(
                credential=credential,
                expected_rp_id=expected_rp_id,
                expected_origin=expected_origin,
                expected_challenge=expected_challenge,
            )

            return {
                "credential_id": bytes_to_base64url(verification.credential_id),
                "public_key": verification.credential_public_key,
                "sign_count": verification.sign_count,
                "transports": credential.response.transports,
                "backed_up": credential.response.authenticator_data.backed_up,
                "uv_available": credential.response.authenticator_data.uv_available,
            }

        except Exception as e:
            raise ValueError(f"WebAuthn registration verification failed: {e}") from e

    def verify_authentication_response(
        self,
        credential: Any,  # AuthenticationCredential or dict from JSON
        expected_rp_id: str,
        expected_origin: str,
        expected_challenge: bytes,
        credential_public_key: bytes,
        credential_current_sign_count: int,
    ) -> dict[str, Any]:
        """Verify WebAuthn authentication response."""

        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_rp_id=expected_rp_id,
                expected_origin=expected_origin,
                expected_challenge=expected_challenge,
                credential_public_key=credential_public_key,
                credential_current_sign_count=credential_current_sign_count,
            )

            return {
                "new_sign_count": verification.new_sign_count,
                "user_verified": verification.user_verified,
            }

        except Exception as e:
            raise ValueError(f"WebAuthn authentication verification failed: {e}") from e


def get_webauthn_manager() -> WebAuthnManager:
    """Get WebAuthn manager instance with configuration from environment."""
    import os

    rp_name = os.getenv("RP_NAME", "FitFolio")
    rp_id = os.getenv("RP_ID", "localhost")
    origin = os.getenv("RP_ORIGIN", "http://localhost:5173")

    return WebAuthnManager(rp_name=rp_name, rp_id=rp_id, origin=origin)
