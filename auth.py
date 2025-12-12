from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")

router = APIRouter(prefix="", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID or "missing-client-id",
    client_secret=GOOGLE_CLIENT_SECRET or "missing-client-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

bearer_scheme = HTTPBearer(auto_error=False)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token",
        ) from exc


def require_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer token",
        )
    token = credentials.credentials
    return decode_access_token(token)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

@router.get("/auth/login", summary="Start OAuth2 login with Google")
async def auth_login(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2 Google client is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    redirect_uri = GOOGLE_REDIRECT_URI or str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", summary="OAuth2 callback that returns service JWT")
async def auth_callback(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2 Google client is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    token = await oauth.google.authorize_access_token(request)
    userinfo: Dict[str, Any] = token.get("userinfo") or {}

    if not userinfo:
        userinfo = await oauth.google.parse_id_token(request, token)

    if not userinfo or "sub" not in userinfo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve user information from Google",
        )

    subject = userinfo["sub"]
    email = userinfo.get("email")

    claims = {
        "sub": subject,
        "email": email,
        "provider": "google",
        "iss": "ms1-user-service",
    }

    access_token = create_access_token(claims)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in_minutes": JWT_EXPIRE_MINUTES,
        "provider_user": {
            "sub": subject,
            "email": email,
        },
    }
