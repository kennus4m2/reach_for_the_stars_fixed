from fastapi import APIRouter, Depends

from app.schemas import QuestionSetIn
from app.security import get_current_host
from app.services import question_set_service as service

router = APIRouter()


@router.post("/question-sets", status_code=201)
def create_question_set(body: QuestionSetIn, host_id: int = Depends(get_current_host)):
    return service.create(host_id, body)


@router.get("/question-sets")
def list_question_sets(host_id: int = Depends(get_current_host)):
    return {"question_sets": service.list_sets(host_id)}


@router.get("/question-sets/{set_id}")
def get_question_set(set_id: int, host_id: int = Depends(get_current_host)):
    return service.get(host_id, set_id)


@router.put("/question-sets/{set_id}")
def replace_question_set(set_id: int, body: QuestionSetIn, host_id: int = Depends(get_current_host)):
    return service.replace(host_id, set_id, body)


@router.delete("/question-sets/{set_id}")
def delete_question_set(set_id: int, host_id: int = Depends(get_current_host)):
    return service.delete(host_id, set_id)
