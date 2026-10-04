import secrets

import psycopg

from app import rules
from app.db import transaction
from app.errors import AppError
from app.repositories import player_repository, question_set_repository, session_repository as repo
from app.security import create_player_token
from app.timeutil import iso
from app.validators import is_bad_nickname


def load(cur, code: str, lock: bool = False):
    """Find a session by join code. Ends it first if the round time ran out."""
    row = repo.get_by_code(cur, code, lock)
    if row is None:
        raise AppError(404, "SESSION_NOT_FOUND", f"No game uses the join code {code[:20]}.")
    if row["expired"]:
        repo.set_ended(cur, row["id"])
        row = repo.get_by_code(cur, code, lock)
    return row


def _public(cur, row) -> dict:
    return {
        "join_code": row["join_code"],
        "status": row["status"],
        "question_set_title": row["question_set_title"],
        "duration_sec": row["duration_sec"],
        "starting_lives": row["starting_lives"],
        "player_count": repo.player_count(cur, row["id"]),
        "max_players": rules.MAX_PLAYERS,
        "seconds_left": row["seconds_left"],
        "started_at": iso(row["started_at"]),
        "ends_at": iso(row["ends_at"]),
        "ended_at": iso(row["ended_at"]),
        "created_at": iso(row["created_at"]),
    }


def _new_code(cur) -> str:
    """6 random digits, never starting with 0, not used by any other session."""
    for _ in range(50):
        code = str(secrets.randbelow(900000) + 100000)
        if not repo.code_exists(cur, code):
            return code
    raise AppError(500, "SERVER_ERROR", "Could not create a join code. Please try again.")


def create(host_id: int, body) -> dict:
    with transaction() as cur:
        qs = question_set_repository.get_set(cur, body.question_set_id)
        if qs is None:
            raise AppError(404, "QUESTION_SET_NOT_FOUND", f"No question set has the id {body.question_set_id}.")
        if qs["host_id"] != host_id:
            raise AppError(403, "NOT_YOUR_QUESTION_SET", "This question set belongs to another host.")
        code = _new_code(cur)
        repo.create(cur, host_id, body.question_set_id, code, body.duration_sec, body.starting_lives)
        return _public(cur, repo.get_by_code(cur, code))


def list_for_host(host_id: int) -> list[dict]:
    with transaction() as cur:
        rows = repo.list_for_host(cur, host_id)
    return [
        {
            "join_code": r["join_code"], "status": r["status"],
            "question_set_title": r["question_set_title"], "player_count": r["player_count"],
            "duration_sec": r["duration_sec"], "starting_lives": r["starting_lives"],
            "started_at": iso(r["started_at"]), "ended_at": iso(r["ended_at"]),
            "created_at": iso(r["created_at"]),
        }
        for r in rows
    ]


def get_public(code: str) -> dict:
    with transaction() as cur:
        return _public(cur, load(cur, code))


def change_status(host_id: int, code: str, new_status: str) -> dict:
    with transaction() as cur:
        row = load(cur, code, lock=True)
        if row["host_id"] != host_id:
            raise AppError(403, "NOT_YOUR_SESSION", "This game belongs to another host.")
        if row["status"] == "ended":
            raise AppError(409, "SESSION_ENDED", "This game has already ended.")
        if new_status == "playing":
            if row["status"] != "waiting":
                raise AppError(409, "INVALID_STATUS_CHANGE", "This game has already started.")
            repo.set_playing(cur, row["id"])
        else:
            repo.set_ended(cur, row["id"])
        return _public(cur, repo.get_by_code(cur, code))


def join(code: str, nickname: str) -> dict:
    with transaction() as cur:
        row = load(cur, code, lock=True)   # lock so two joins cannot pass the limit together
        if row["status"] == "ended":
            raise AppError(409, "SESSION_ENDED", "This game has already ended.")
        if repo.player_count(cur, row["id"]) >= rules.MAX_PLAYERS:
            raise AppError(409, "SESSION_FULL", "This game is full.")
        if is_bad_nickname(nickname):
            raise AppError(400, "NICKNAME_NOT_ALLOWED", "Please pick a different nickname.")
        if player_repository.nickname_taken(cur, row["id"], nickname):
            raise AppError(409, "NICKNAME_TAKEN", "That nickname is already used in this game.")
        try:
            player_id = player_repository.create(cur, row["id"], nickname, row["starting_lives"])
        except psycopg.errors.UniqueViolation:
            raise AppError(409, "NICKNAME_TAKEN", "That nickname is already used in this game.")
        return {
            "player_id": player_id,
            "nickname": nickname,
            "token": create_player_token(player_id, row["id"]),
            "token_type": "Bearer",
            "expires_in": 3 * 3600,
            "stars": 0,
            "lives": row["starting_lives"],
            "session_status": row["status"],
        }
