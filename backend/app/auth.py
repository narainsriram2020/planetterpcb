"""Supabase Auth: verify the access token the web app sends with each chat request.

Supabase signs access tokens with an asymmetric key (ES256) published at the
project's JWKS endpoint, so tokens are verified locally without a network call
per request (the key set is fetched once and cached).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request

from planetterp_mcp import config  # noqa: F401 - loads .env before the getenv calls below

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/") or None
# Chat requires sign-in whenever Supabase is configured; REQUIRE_AUTH=false opts out for local testing.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true" if SUPABASE_URL else "false").lower() in {"1", "true", "yes"}

_jwks = (
    jwt.PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_jwk_set=True, lifespan=3600)
    if SUPABASE_URL
    else None
)


@dataclass(frozen=True)
class User:
    id: str
    email: str | None


def _decode(token: str) -> dict:
    signing_key = _jwks.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=f"{SUPABASE_URL}/auth/v1",
    )


async def current_user(request: Request) -> User | None:
    """The signed-in user, or None for anonymous requests when sign-in isn't required."""
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not token or _jwks is None:
        if REQUIRE_AUTH:
            raise HTTPException(status_code=401, detail="Sign in to chat with TerpGuide.")
        return None
    try:
        claims = await asyncio.to_thread(_decode, token)
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise HTTPException(status_code=401, detail="Your session expired. Sign in again.") from exc
    return User(id=claims["sub"], email=claims.get("email"))
