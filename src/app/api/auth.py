"""JWT authentication for admin panel."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.shared.config import settings

auth_router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

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
