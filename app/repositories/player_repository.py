"""All SQL for players and the leaderboard."""

# Rank: most stars, then most correct answers, then fastest average answer.
# Players who are equal on all three share a rank.
_RANKED = """
    SELECT id, nickname, stars, correct_count, best_streak, current_streak, lives,
           double_star_ready, protection_ready,
           RANK() OVER (
               ORDER BY stars DESC, correct_count DESC,
                        (total_answer_ms::float / NULLIF(answer_count, 0)) ASC NULLS LAST
           ) AS rank
    FROM session_players WHERE session_id = %s
"""


def create(cur, session_id: int, nickname: str, lives: int):
    cur.execute(
        "INSERT INTO session_players (session_id, nickname, lives) VALUES (%s, %s, %s) RETURNING id",
        (session_id, nickname, lives),
    )
    return cur.fetchone()["id"]


def nickname_taken(cur, session_id: int, nickname: str) -> bool:
    cur.execute(
        "SELECT 1 FROM session_players WHERE session_id = %s AND LOWER(nickname) = LOWER(%s)",
        (session_id, nickname),
    )
    return cur.fetchone() is not None


def get(cur, player_id: int, lock: bool = False):
    sql = "SELECT * FROM session_players WHERE id = %s"
    if lock:
        sql += " FOR UPDATE"
    cur.execute(sql, (player_id,))
    return cur.fetchone()


def get_ranked(cur, session_id: int, player_id: int):
    cur.execute(f"SELECT * FROM ({_RANKED}) r WHERE r.id = %s", (session_id, player_id))
    return cur.fetchone()


def leaderboard(cur, session_id: int):
    cur.execute(f"SELECT * FROM ({_RANKED}) r ORDER BY r.rank, r.id", (session_id,))
    return cur.fetchall()


def set_current_question(cur, player_id: int, question_id: int) -> None:
    cur.execute(
        "UPDATE session_players SET current_question_id = %s, question_served_at = NOW() WHERE id = %s",
        (question_id, player_id),
    )


def elapsed_ms(cur, player_id: int) -> int:
    cur.execute(
        "SELECT (EXTRACT(EPOCH FROM (clock_timestamp() - question_served_at)) * 1000)::bigint AS ms "
        "FROM session_players WHERE id = %s",
        (player_id,),
    )
    return cur.fetchone()["ms"]


def update_after_answer(cur, player_id: int, *, stars: int, lives: int, streak: int, correct: bool,
                        time_ms: int, double_star_ready: bool, protection_ready: bool) -> None:
    cur.execute(
        "UPDATE session_players SET stars = %s, lives = %s, current_streak = %s, "
        "best_streak = GREATEST(best_streak, %s), correct_count = correct_count + %s, "
        "answer_count = answer_count + 1, total_answer_ms = total_answer_ms + %s, "
        "double_star_ready = %s, protection_ready = %s, "
        "current_question_id = NULL, question_served_at = NULL WHERE id = %s",
        (stars, lives, streak, streak, 1 if correct else 0, time_ms,
         double_star_ready, protection_ready, player_id),
    )


def set_ready_flag(cur, player_id: int, column: str) -> None:
    assert column in ("double_star_ready", "protection_ready")
    cur.execute(f"UPDATE session_players SET {column} = TRUE WHERE id = %s", (player_id,))
