from app.db import transaction
from app.errors import AppError
from app.repositories import question_set_repository as repo
from app.timeutil import iso


def _owned_set(cur, host_id: int, set_id: int):
    header = repo.get_set(cur, set_id)
    if header is None:
        raise AppError(404, "QUESTION_SET_NOT_FOUND", f"No question set has the id {set_id}.")
    if header["host_id"] != host_id:
        raise AppError(403, "NOT_YOUR_QUESTION_SET", "This question set belongs to another host.")
    return header


def _shape(cur, set_id: int) -> dict:
    """Hub Contract Rule 3 shape, plus id and created_at."""
    header, questions = repo.get_full(cur, set_id)
    return {
        "id": header["id"],
        "title": header["title"],
        "description": header["description"],
        "subject": header["subject"],
        "grade_level": header["grade_level"],
        "questions": questions,
        "created_at": iso(header["created_at"]),
    }


def create(host_id: int, data) -> dict:
    with transaction() as cur:
        set_id = repo.insert_set(cur, host_id, data)
        return _shape(cur, set_id)


def list_sets(host_id: int) -> list[dict]:
    with transaction() as cur:
        rows = repo.list_for_host(cur, host_id)
    return [{**r, "created_at": iso(r["created_at"])} for r in rows]


def get(host_id: int, set_id: int) -> dict:
    with transaction() as cur:
        _owned_set(cur, host_id, set_id)
        return _shape(cur, set_id)


def replace(host_id: int, set_id: int, data) -> dict:
    with transaction() as cur:
        _owned_set(cur, host_id, set_id)
        if repo.count_sessions(cur, set_id) > 0:
            raise AppError(409, "QUESTION_SET_IN_USE", "This set was already used in a game and cannot be changed.")
        repo.update_set(cur, set_id, data)
        return _shape(cur, set_id)


def delete(host_id: int, set_id: int) -> dict:
    with transaction() as cur:
        _owned_set(cur, host_id, set_id)
        if repo.count_sessions(cur, set_id) > 0:
            raise AppError(409, "QUESTION_SET_IN_USE", "This set was already used in a game and cannot be deleted.")
        repo.delete_set(cur, set_id)
    return {"deleted": True, "id": set_id}
