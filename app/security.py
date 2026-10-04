import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errors import AppError

HOST_TOKEN_HOURS = 8
PLAYER_TOKEN_HOURS = 3   # Hub Contract: player token expires after 3 hours
_bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set in .env")
    return secret


def hash_password(password: str) -> str:
    # bcrypt only reads the first 72 bytes
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())


def _make_token(claims: dict, hours: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + timedelta(hours=hours)}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def create_host_token(host_id: int) -> str:
    return _make_token({"sub": str(host_id), "role": "host"}, HOST_TOKEN_HOURS)


def create_player_token(player_id: int, session_id: int) -> str:
    """Valid for one session only (the session id is inside the token)."""
    return _make_token({"sub": str(player_id), "role": "player", "sid": session_id}, PLAYER_TOKEN_HOURS)


def _decode(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None:
        raise AppError(401, "AUTH_REQUIRED", "Please log in first.")
    try:
        return jwt.decode(credentials.credentials, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise AppError(401, "AUTH_REQUIRED", "Your login is invalid or has expired.")


def get_current_host(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> int:
    """Dependency for host-only endpoints. Returns the host id."""
    payload = _decode(credentials)
    if payload.get("role") != "host":
        raise AppError(403, "FORBIDDEN", "Only hosts can do this.")
    return int(payload["sub"])


def get_current_player(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Dependency for player endpoints. Returns {"player_id", "session_id"}."""
    payload = _decode(credentials)
    if payload.get("role") != "player":
        raise AppError(403, "FORBIDDEN", "Only players can do this.")
    return {"player_id": int(payload["sub"]), "session_id": int(payload["sid"])}
