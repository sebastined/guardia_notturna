"""JWT issuance and role-based access control.

The single auth model for the platform. Services sit behind this gateway and
trust the `Actor` it resolves; they do not implement their own auth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gn_schemas import Actor
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

    @property
    def rank(self) -> int:
        return {Role.VIEWER: 0, Role.ANALYST: 1, Role.ADMIN: 2}[self]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    *, subject: str, email: str | None, role: Role, expires: timedelta | None = None
) -> str:
    now = datetime.now(timezone.utc)
    expiry = now + (expires or timedelta(minutes=settings.jwt_expire_minutes))
    claims = {
        "sub": subject,
        "email": email,
        "role": role.value,
        "iat": now,
        "exp": expiry,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Actor:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return Actor(
        subject=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role", Role.VIEWER.value),
    )


def require_role(minimum: Role):
    """Dependency factory enforcing a minimum role.

    Roles are ranked, so `require_role(Role.ANALYST)` admits analysts and admins.
    """

    def _guard(actor: Actor = Depends(current_actor)) -> Actor:
        try:
            held = Role(actor.role)
        except ValueError:
            held = Role.VIEWER
        if held.rank < minimum.rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} role or higher.",
            )
        return actor

    return _guard
