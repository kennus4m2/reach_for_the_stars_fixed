from fastapi import APIRouter, Depends

from app.schemas import JoinRequest
from app.security import get_current_player
from app.services import game_service, session_service

router = APIRouter()


@router.post("/sessions/{code}/players", status_code=201)
def join_session(code: str, body: JoinRequest):
    return session_service.join(code, body.nickname)


@router.get("/sessions/{code}/players/me")
def my_state(code: str, who: dict = Depends(get_current_player)):
    return game_service.me(code, who)
