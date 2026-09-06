"""JWT authentication for admin panel."""

from __future__ import annotations

import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.shared.config import settings

auth_router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])
tma_auth_router = APIRouter(prefix="/api/tma", tags=["tma-auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/auth/login")


class LoginRequest(BaseModel):
    """Request body for admin login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Response containing JWT access token."""

    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """Current user info returned by /me."""

    username: str
    role: str


def create_access_token(data: dict) -> str:
    """Encode a JWT token with the given payload.

    Uses HS256 algorithm with secret from settings. Token expires in 24 hours.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Raises JWTError if the token is invalid or expired.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate admin user and return JWT token.

    Validates credentials against admin username/password from environment.
    Returns 401 for invalid credentials.
    """
    if request.username != settings.ADMIN_USERNAME or request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": request.username, "role": "admin"})
    return TokenResponse(access_token=access_token)


@auth_router.get("/me", response_model=UserInfo)
async def me(token: str = Depends(oauth2_scheme)) -> UserInfo:
    """Return current user info from JWT.

    Decodes the token and returns username and role.
    """
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    role = payload.get("role", "admin")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInfo(username=username, role=role)


# ---------------------------------------------------------------------------
# Telegram Mini App (TMA) authentication
# ---------------------------------------------------------------------------

ADMIN_ROLES = {"master", "leader", "curator"}


class TMAAuthRequest(BaseModel):
    """Request body for TMA login — raw initData string from Telegram WebApp."""

    initData: str


def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """Validate Telegram Mini App initData using HMAC-SHA256.

    Returns the parsed user dict if valid, None otherwise.

    Algorithm (per Telegram Bot API docs):
        1. Parse initData into key=value pairs (URL-decoded).
        2. Remove 'hash' from the dict.
        3. Sort remaining keys alphabetically.
        4. Build data_check_string = '\\n'.join(f'{k}={v}' for k, v in sorted).
        5. secret_key = HMAC-SHA256(key=b"WebAppData", msg=bot_token).
        6. computed = HMAC-SHA256(key=secret_key, msg=data_check_string).hexdigest().
        7. Compare computed == hash.
    """
    if not bot_token:
        return None

    # Parse initData into dict
    params = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in params:
        return None

    received_hash = params.pop("hash")

    # Build data-check-string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # HMAC-SHA256 validation
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if computed_hash != received_hash:
        return None

    # Extract user data
    user_json = params.get("user")
    if not user_json:
        return None

    try:
        return json.loads(user_json)
    except (json.JSONDecodeError, TypeError):
        return None


@tma_auth_router.post("/auth")
async def tma_login(request: TMAAuthRequest) -> TokenResponse:
    """Authenticate a Telegram Mini App user via initData.

    Validates the initData HMAC, looks up the user in the DB,
    and returns a JWT if the user has an admin role.
    """
    bot_token = settings.effective_tma_token
    user_data = validate_telegram_init_data(request.initData, bot_token)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        )

    telegram_id = user_data.get("id")
    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user id in initData",
        )

    # Look up user in DB
    from sqlalchemy import select
    from app.shared.database import session_factory
    from app.shared.models.user import User

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )

    if user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role}' is not authorized for admin access",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    return TokenResponse(access_token=access_token)
