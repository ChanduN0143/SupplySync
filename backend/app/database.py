import sqlite3
from pathlib import Path
from contextlib import contextmanager

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "supplysync.db"


def get_connection():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection


@contextmanager
def get_db():
    connection = get_connection()

    try:
        yield connection
    finally:
        connection.close()