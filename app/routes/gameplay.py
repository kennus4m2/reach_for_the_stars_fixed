from fastapi import APIRouter, Depends

from app.schemas import AnswerRequest, ChestRequest
from app.security import get_current_player
from app.services import game_service

router = APIRouter()


@router.get("/sessions/{code}/questions/next")
def next_question(code: str, who: dict = Depends(get_current_player)):
    return game_service.next_question(code, who)


@router.post("/sessions/{code}/answers", status_code=201)
def submit_answer(code: str, body: AnswerRequest, who: dict = Depends(get_current_player)):
    return game_service.submit_answer(code, who, body)


@router.post("/sessions/{code}/chests", status_code=201)
def open_chest(code: str, body: ChestRequest, who: dict = Depends(get_current_player)):
    return game_service.open_chest(code, who, body)


@router.get("/sessions/{code}/leaderboard")
def leaderboard(code: str):
    return game_service.leaderboard(code)
