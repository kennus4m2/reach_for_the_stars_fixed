from fastapi import APIRouter, Depends

from app.schemas import SessionCreate, SessionPatch
from app.security import get_current_host
from app.services import session_service as service

router = APIRouter()


@router.post("/sessions", status_code=201)
def create_session(body: SessionCreate, host_id: int = Depends(get_current_host)):
    return service.create(host_id, body)


@router.get("/sessions")
def list_sessions(host_id: int = Depends(get_current_host)):
    return {"sessions": service.list_for_host(host_id)}


@router.get("/sessions/{code}")
def get_session(code: str):
    return service.get_public(code)


@router.patch("/sessions/{code}")
def change_session_status(code: str, body: SessionPatch, host_id: int = Depends(get_current_host)):
    return service.change_status(host_id, code, body.status)
