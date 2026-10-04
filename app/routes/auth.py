from fastapi import APIRouter

from app.db import transaction
from app.errors import AppError
from app.repositories import host_repository
from app.schemas import LoginRequest
from app.security import HOST_TOKEN_HOURS, create_host_token, verify_password

router = APIRouter()


@router.post("/auth/login")
def login(body: LoginRequest):
    with transaction() as cur:
        host = host_repository.get_by_username(cur, body.username)

    # Same message for a wrong username and a wrong password
    if host is None or not verify_password(body.password, host["password_hash"]):
        raise AppError(401, "INVALID_CREDENTIALS", "The username or password is wrong.")

    return {
        "token": create_host_token(host["id"]),
        "token_type": "Bearer",
        "expires_in": HOST_TOKEN_HOURS * 3600,
        "host": {"id": host["id"], "username": host["username"], "display_name": host["display_name"]},
    }
