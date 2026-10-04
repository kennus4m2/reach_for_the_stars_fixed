"""All SQL for sessions."""


def code_exists(cur, code: str) -> bool:
    cur.execute("SELECT 1 FROM sessions WHERE join_code = %s", (code,))
    return cur.fetchone() is not None


def create(cur, host_id: int, set_id: int, code: str, duration_sec: int, lives: int):
    cur.execute(
        "INSERT INTO sessions (host_id, question_set_id, join_code, duration_sec, starting_lives) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (host_id, set_id, code, duration_sec, lives),
    )
    return cur.fetchone()["id"]


def get_by_code(cur, code: str, lock: bool = False):
    """Returns the session plus `expired` (playing, but the round time ran out)."""
    sql = (
        "SELECT s.*, qs.title AS question_set_title, "
        "       (s.status = 'playing' AND s.ends_at < NOW()) AS expired, "
        "       CASE WHEN s.status = 'playing' "
        "            THEN GREATEST(0, EXTRACT(EPOCH FROM (s.ends_at - NOW()))::int) END AS seconds_left "
        "FROM sessions s JOIN question_sets qs ON qs.id = s.question_set_id "
        "WHERE s.join_code = %s"
    )
    if lock:
        sql += " FOR UPDATE OF s"
    cur.execute(sql, (code,))
    return cur.fetchone()


def list_for_host(cur, host_id: int):
    cur.execute(
        "SELECT s.id, s.join_code, s.status, s.duration_sec, s.starting_lives, s.started_at, "
        "       s.ends_at, s.ended_at, s.created_at, qs.title AS question_set_title, "
        "       (SELECT COUNT(*) FROM session_players p WHERE p.session_id = s.id) AS player_count "
        "FROM sessions s JOIN question_sets qs ON qs.id = s.question_set_id "
        "WHERE s.host_id = %s ORDER BY s.id DESC",
        (host_id,),
    )
    return cur.fetchall()


def player_count(cur, session_id: int) -> int:
    cur.execute("SELECT COUNT(*) AS n FROM session_players WHERE session_id = %s", (session_id,))
    return cur.fetchone()["n"]


def set_playing(cur, session_id: int) -> None:
    cur.execute(
        "UPDATE sessions SET status = 'playing', started_at = NOW(), "
        "ends_at = NOW() + duration_sec * INTERVAL '1 second' WHERE id = %s",
        (session_id,),
    )


def set_ended(cur, session_id: int) -> None:
    # If the time simply ran out, the end time is when it ran out
    cur.execute(
        "UPDATE sessions SET status = 'ended', ended_at = LEAST(ends_at, NOW()) WHERE id = %s",
        (session_id,),
    )
