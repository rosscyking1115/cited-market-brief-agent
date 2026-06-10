"""API authentication (plan §9: OIDC Authorization Code + PKCE at the IdP; the API
validates the resulting JWT bearer tokens against the provider's JWKS).

Modes:
- AUTH_REQUIRED=false (development default): requests pass; tenant context comes
  from the dev org. Never deploy multi-tenant like this — Phase 5 gate.
- AUTH_REQUIRED=true: every non-health request needs a valid Bearer JWT
  (signature via JWKS, issuer + audience enforced). The org_id claim becomes the
  request's tenant context, which get_db turns into the RLS GUC.

Expected claims: sub, email, org_id (UUID string). MFA/SSO/SCIM live at the IdP.
"""

from functools import lru_cache

from fastapi import HTTPException, Request

from app.core.config import settings

_BEARER = "bearer"


@lru_cache(maxsize=1)
def _jwks_client():
    import jwt  # noqa: PLC0415 — PyJWT, lazy

    if not settings.oidc_jwks_url:
        raise RuntimeError("AUTH_REQUIRED=true but OIDC_JWKS_URL is not configured")
    return jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True)


def _validate_token(token: str) -> dict:
    import jwt  # noqa: PLC0415

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            issuer=settings.oidc_issuer or None,
            audience=settings.oidc_audience or None,
            options={"require": ["exp", "iat", "sub"]},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_auth(request: Request) -> None:
    """Router-level dependency. Sets request.state.org_id / user claims when
    authenticated; no-ops in development mode."""
    if not settings.auth_required:
        return

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != _BEARER or not token:
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _validate_token(token)
    org_id = claims.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="Token missing org_id claim")

    request.state.org_id = org_id
    request.state.user_sub = claims.get("sub")
    request.state.user_email = claims.get("email")
