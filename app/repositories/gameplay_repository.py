"""All SQL for questions served to players, answers and chests."""
from app import rules


def next_question(cur, set_id: int, player_id: int):
    cur.execute(
        "SELECT q.id, q.position, q.text, q.type, q.time_limit_sec FROM questions q "
        "WHERE q.question_set_id = %s "
        "AND NOT EXISTS (SELECT 1 FROM answers a WHERE a.player_id = %s AND a.question_id = q.id) "
        "ORDER BY q.position LIMIT 1",
        (set_id, player_id),
    )
    return cur.fetchone()


def get_choices(cur, question_id: int) -> list[str]:
    # correct answers are never selected here
    cur.execute(
        "SELECT text FROM choices WHERE question_id = %s ORDER BY choice_index", (question_id,)
    )
    return [row["text"] for row in cur.fetchall()]


def count_questions(cur, set_id: int) -> int:
    cur.execute("SELECT COUNT(*) AS n FROM questions WHERE question_set_id = %s", (set_id,))
    return cur.fetchone()["n"]


def get_question(cur, question_id: int):
    cur.execute(
        "SELECT id, question_set_id, time_limit_sec FROM questions WHERE id = %s", (question_id,)
    )
    return cur.fetchone()


def get_choice(cur, question_id: int, choice_index: int):
    cur.execute(
        "SELECT id, is_correct FROM choices WHERE question_id = %s AND choice_index = %s",
        (question_id, choice_index),
    )
    return cur.fetchone()


def already_answered(cur, player_id: int, question_id: int) -> bool:
    cur.execute(
        "SELECT 1 FROM answers WHERE player_id = %s AND question_id = %s", (player_id, question_id)
    )
    return cur.fetchone() is not None


def insert_answer(cur, *, player_id, question_id, choice_id, is_correct, time_ms, stars_change,
                  streak_after, double_star_used, protection_used) -> int:
    cur.execute(
        "INSERT INTO answers (player_id, question_id, choice_id, is_correct, answer_time_ms, "
        "stars_earned, streak_after, double_star_used, protection_used) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (player_id, question_id, choice_id, is_correct, time_ms, stars_change,
         streak_after, double_star_used, protection_used),
    )
    return cur.fetchone()["id"]


def remaining_questions(cur, set_id: int, player_id: int) -> int:
    cur.execute(
        "SELECT COUNT(*) AS n FROM questions q WHERE q.question_set_id = %s "
        "AND NOT EXISTS (SELECT 1 FROM answers a WHERE a.player_id = %s AND a.question_id = q.id)",
        (set_id, player_id),
    )
    return cur.fetchone()["n"]


# ---------- chests ----------

def create_chest(cur, answer_id: int, player_id: int, slots: list[str]) -> int:
    cur.execute(
        "INSERT INTO chest_offers (answer_id, player_id) VALUES (%s, %s) RETURNING id",
        (answer_id, player_id),
    )
    offer_id = cur.fetchone()["id"]
    for number, reward in enumerate(slots, start=1):
        cur.execute(
            "INSERT INTO chest_slots (chest_offer_id, slot_number, reward_type) VALUES (%s, %s, %s)",
            (offer_id, number, reward),
        )
    return offer_id


def pending_chest(cur, player_id: int):
    cur.execute(
        "SELECT id, (created_at + %s * INTERVAL '1 second' < NOW()) AS expired "
        "FROM chest_offers WHERE player_id = %s AND status = 'offered' ORDER BY id DESC LIMIT 1",
        (rules.CHEST_TIMEOUT_SEC, player_id),
    )
    return cur.fetchone()


def get_chest(cur, offer_id: int, player_id: int):
    cur.execute(
        "SELECT id, status, (created_at + %s * INTERVAL '1 second' < NOW()) AS expired "
        "FROM chest_offers WHERE id = %s AND player_id = %s FOR UPDATE",
        (rules.CHEST_TIMEOUT_SEC, offer_id, player_id),
    )
    return cur.fetchone()


def get_slot_reward(cur, offer_id: int, slot_number: int):
    cur.execute(
        "SELECT reward_type FROM chest_slots WHERE chest_offer_id = %s AND slot_number = %s",
        (offer_id, slot_number),
    )
    row = cur.fetchone()
    return row["reward_type"] if row else None


def mark_chest(cur, offer_id: int, status: str, picked_slot: int | None = None) -> None:
    cur.execute(
        "UPDATE chest_offers SET status = %s, picked_slot = %s, "
        "opened_at = CASE WHEN %s = 'opened' THEN NOW() ELSE opened_at END WHERE id = %s",
        (status, picked_slot, status, offer_id),
    )
