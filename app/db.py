import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def get_connection():
    """Open a PostgreSQL connection using the values in .env.

    The team schema is set as the search path, so SQL can say
    "FROM hosts" instead of "FROM reach_for_the_stars.hosts".
    Rows come back as dictionaries (row["name"]).
    """
    schema = os.getenv("DB_SCHEMA", "reach_for_the_stars")
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        connect_timeout=15,
        options=f"-c search_path={schema} -c TimeZone=UTC",
        row_factory=dict_row,
    )


@contextmanager
def transaction():
    """One database transaction. Commits on success, rolls back on any error."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
