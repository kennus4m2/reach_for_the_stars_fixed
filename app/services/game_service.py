from app import rules
from app.db import transaction
from app.errors import AppError
from app.repositories import gameplay_repository as game
from app.repositories import player_repository as players
from app.services import session_service

REWARD_MESSAGES = {
    "double_star": "Double Star! Your next correct answer earns 2x stars.",
    "protection_card": "Protection Card! Your next wrong answer will not cost stars or break your streak.",
    "empty": "Better luck next time! This chest was empty.",
}


def _context(cur, code: str, who: dict, lock_player: bool = True):
    session = session_service.load(cur, code)
    if who["session_id"] != session["id"]:
        raise AppError(403, "WRONG_SESSION", "Your player token is for a different game.")
    player = players.get(cur, who["player_id"], lock=lock_player)
    if player is None:
        raise AppError(401, "AUTH_REQUIRED", "This player no longer exists. Please join again.")
    return session, player


def _require_playing(session) -> None:
    if session["status"] == "ended":
        raise AppError(409, "SESSION_ENDED", "This game has ended.")
    if session["status"] == "waiting":
        raise AppError(409, "SESSION_NOT_STARTED", "The host has not started the game yet.")


def _handle_pending_chest(cur, player) -> None:
    """An unopened chest blocks the next question until it is opened or expires."""
    chest = game.pending_chest(cur, player["id"])
    if chest is None:
        return
    if chest["expired"]:
        game.mark_chest(cur, chest["id"], "expired")
    else:
        raise AppError(409, "CHEST_PENDING", "Open your mystery chest first.")


# ---------- player state ----------

def me(code: str, who: dict) -> dict:
    with transaction() as cur:
        session, player = _context(cur, code, who, lock_player=False)
        ranked = players.get_ranked(cur, session["id"], player["id"])
        return {
            "nickname": player["nickname"],
            "stars": player["stars"],
            "lives": player["lives"],
            "streak": player["current_streak"],
            "best_streak": player["best_streak"],
            "correct_count": player["correct_count"],
            "double_star_ready": player["double_star_ready"],
            "protection_ready": player["protection_ready"],
            "rank": ranked["rank"],
            "session_status": session["status"],
            "seconds_left": session["seconds_left"],
        }


# ---------- questions ----------

def next_question(code: str, who: dict) -> dict:
    with transaction() as cur:
        session, player = _context(cur, code, who)
        _require_playing(session)
        if player["lives"] <= 0:
            return {"finished": True, "reason": "out_of_lives"}
        _handle_pending_chest(cur, player)

        q = game.next_question(cur, session["question_set_id"], player["id"])
        if q is None:
            return {"finished": True, "reason": "no_more_questions"}

        # The timer starts the first time a question is served. Asking again
        # does not restart it.
        if player["current_question_id"] != q["id"]:
            players.set_current_question(cur, player["id"], q["id"])

        return {
            "finished": False,
            "question": {
                "id": q["id"],
                "number": q["position"],
                "total": game.count_questions(cur, session["question_set_id"]),
                "text": q["text"],
                "type": q["type"],
                "choices": game.get_choices(cur, q["id"]),   # no correct answer
                "time_limit_sec": q["time_limit_sec"],
            },
        }


# ---------- answers ----------

def submit_answer(code: str, who: dict, body) -> dict:
    with transaction() as cur:
        session, player = _context(cur, code, who)
        _require_playing(session)
        if player["lives"] <= 0:
            raise AppError(409, "PLAYER_OUT_OF_LIVES", "You have no lives left.")
        _handle_pending_chest(cur, player)

        if player["current_question_id"] != body.question_id or player["question_served_at"] is None:
            raise AppError(409, "QUESTION_NOT_ACTIVE", "Ask for the question first, then answer it.")
        if game.already_answered(cur, player["id"], body.question_id):
            raise AppError(409, "ALREADY_ANSWERED", "You already answered this question.")

        question = game.get_question(cur, body.question_id)
        choice = game.get_choice(cur, body.question_id, body.choice_index)
        if choice is None:
            raise AppError(400, "VALIDATION_FAILED", "choice_index: that choice does not exist for this question.")

        # The server measures the time, never the player's device
        limit_ms = question["time_limit_sec"] * 1000
        elapsed = players.elapsed_ms(cur, player["id"])
        late = elapsed > limit_ms + rules.ANSWER_GRACE_MS
        correct = bool(choice["is_correct"]) and not late

        if correct:
            result = rules.score_correct(player["stars"], player["current_streak"], player["double_star_ready"])
            lives = player["lives"]
            double_ready = False
            protection_ready = player["protection_ready"]
        else:
            result = rules.score_wrong(player["stars"], player["current_streak"], player["protection_ready"])
            lives = player["lives"] - 1          # a wrong answer or timeout always costs a life
            double_ready = player["double_star_ready"]
            protection_ready = False if result["protection_used"] else player["protection_ready"]

        time_ms = min(elapsed, limit_ms)
        answer_id = game.insert_answer(
            cur, player_id=player["id"], question_id=body.question_id,
            choice_id=None if late else choice["id"], is_correct=correct, time_ms=time_ms,
            stars_change=result["stars_change"], streak_after=result["streak"],
            double_star_used=result["double_star_used"], protection_used=result["protection_used"],
        )
        players.update_after_answer(
            cur, player["id"], stars=result["stars"], lives=lives, streak=result["streak"],
            correct=correct, time_ms=time_ms, double_star_ready=double_ready,
            protection_ready=protection_ready,
        )

        chest = None
        if correct and rules.chest_earned(result["streak"]):
            offer_id = game.create_chest(cur, answer_id, player["id"], rules.make_chest_slots())
            chest = {"chest_offer_id": offer_id, "chests": rules.CHEST_COUNT,
                     "expires_in_sec": rules.CHEST_TIMEOUT_SEC}

        finished_reason = None
        if lives <= 0:
            finished_reason = "out_of_lives"
        elif game.remaining_questions(cur, session["question_set_id"], player["id"]) == 0:
            finished_reason = "no_more_questions"

        ranked = players.get_ranked(cur, session["id"], player["id"])
        return {
            "correct": correct,
            "timed_out": late,
            "stars_change": result["stars_change"],
            "stars": result["stars"],
            "streak": result["streak"],
            "lives": lives,
            "double_star_used": result["double_star_used"],
            "protection_used": result["protection_used"],
            "rank": ranked["rank"],
            "chest_offer": chest,
            "finished": finished_reason is not None,
            "finished_reason": finished_reason,
        }


# ---------- chests ----------

def open_chest(code: str, who: dict, body) -> dict:
    with transaction() as cur:
        session, player = _context(cur, code, who)
        if session["status"] == "ended":
            raise AppError(409, "SESSION_ENDED", "This game has ended.")

        chest = game.get_chest(cur, body.chest_offer_id, player["id"])
        if chest is None:
            raise AppError(404, "CHEST_NOT_FOUND", "No chest with that id.")
        if chest["status"] == "opened":
            raise AppError(409, "CHEST_ALREADY_OPENED", "You already opened this chest.")
        if chest["status"] == "expired" or chest["expired"]:
            raise AppError(409, "CHEST_EXPIRED", "This chest expired.")

        reward = game.get_slot_reward(cur, chest["id"], body.slot_number)
        game.mark_chest(cur, chest["id"], "opened", body.slot_number)
        if reward == "double_star":
            players.set_ready_flag(cur, player["id"], "double_star_ready")
        elif reward == "protection_card":
            players.set_ready_flag(cur, player["id"], "protection_ready")

        fresh = players.get(cur, player["id"])
        return {
            "reward": reward,
            "message": REWARD_MESSAGES[reward],
            "double_star_ready": fresh["double_star_ready"],
            "protection_ready": fresh["protection_ready"],
        }


# ---------- leaderboard ----------

def leaderboard(code: str) -> dict:
    with transaction() as cur:
        session = session_service.load(cur, code)
        rows = players.leaderboard(cur, session["id"])
        return {
            "join_code": session["join_code"],
            "status": session["status"],
            "seconds_left": session["seconds_left"],
            "players": [
                {
                    "rank": r["rank"], "nickname": r["nickname"], "stars": r["stars"],
                    "correct_count": r["correct_count"], "best_streak": r["best_streak"],
                    "lives": r["lives"],
                }
                for r in rows
            ],
        }
