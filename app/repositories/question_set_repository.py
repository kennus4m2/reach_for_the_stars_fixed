"""All SQL for question sets, questions and choices."""


def insert_set(cur, host_id: int, data) -> int:
    cur.execute(
        "INSERT INTO question_sets (host_id, title, description, subject, grade_level) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (host_id, data.title, data.description, data.subject, data.grade_level),
    )
    set_id = cur.fetchone()["id"]
    insert_questions(cur, set_id, data.questions)
    return set_id


def insert_questions(cur, set_id: int, questions) -> None:
    for position, q in enumerate(questions, start=1):
        cur.execute(
            "INSERT INTO questions (question_set_id, position, text, type, time_limit_sec) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (set_id, position, q.text, q.type, q.time_limit_sec),
        )
        question_id = cur.fetchone()["id"]
        for index, text in enumerate(q.choices):
            cur.execute(
                "INSERT INTO choices (question_id, choice_index, text, is_correct) "
                "VALUES (%s, %s, %s, %s)",
                (question_id, index, text, index == q.correct_index),
            )


def get_set(cur, set_id: int):
    cur.execute(
        "SELECT id, host_id, title, description, subject, grade_level, created_at "
        "FROM question_sets WHERE id = %s",
        (set_id,),
    )
    return cur.fetchone()


def get_full(cur, set_id: int):
    """The question set in the Hub Contract Rule 3 shape (host view, includes correct_index)."""
    header = get_set(cur, set_id)
    if header is None:
        return None
    cur.execute(
        "SELECT q.id, q.position, q.text, q.type, q.time_limit_sec, "
        "       c.choice_index, c.text AS choice_text, c.is_correct "
        "FROM questions q JOIN choices c ON c.question_id = q.id "
        "WHERE q.question_set_id = %s ORDER BY q.position, c.choice_index",
        (set_id,),
    )
    questions: dict[int, dict] = {}
    for row in cur.fetchall():
        q = questions.setdefault(row["id"], {
            "text": row["text"], "type": row["type"], "choices": [],
            "correct_index": None, "time_limit_sec": row["time_limit_sec"],
        })
        q["choices"].append(row["choice_text"])
        if row["is_correct"]:
            q["correct_index"] = row["choice_index"]
    return header, list(questions.values())


def list_for_host(cur, host_id: int):
    cur.execute(
        "SELECT s.id, s.title, s.description, s.subject, s.grade_level, s.created_at, "
        "       (SELECT COUNT(*) FROM questions q WHERE q.question_set_id = s.id) AS question_count "
        "FROM question_sets s WHERE s.host_id = %s ORDER BY s.id DESC",
        (host_id,),
    )
    return cur.fetchall()


def update_set(cur, set_id: int, data) -> None:
    cur.execute(
        "UPDATE question_sets SET title = %s, description = %s, subject = %s, grade_level = %s "
        "WHERE id = %s",
        (data.title, data.description, data.subject, data.grade_level, set_id),
    )
    cur.execute("DELETE FROM questions WHERE question_set_id = %s", (set_id,))
    insert_questions(cur, set_id, data.questions)


def delete_set(cur, set_id: int) -> None:
    cur.execute("DELETE FROM question_sets WHERE id = %s", (set_id,))


def count_sessions(cur, set_id: int) -> int:
    cur.execute("SELECT COUNT(*) AS n FROM sessions WHERE question_set_id = %s", (set_id,))
    return cur.fetchone()["n"]
