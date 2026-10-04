def get_by_username(cur, username: str):
    cur.execute(
        "SELECT id, username, password_hash, display_name FROM hosts WHERE username = %s",
        (username,),
    )
    return cur.fetchone()


def create(cur, username: str, password_hash: str, display_name: str) -> int:
    cur.execute(
        "INSERT INTO hosts (username, password_hash, display_name) VALUES (%s, %s, %s) RETURNING id",
        (username, password_hash, display_name),
    )
    return cur.fetchone()["id"]
