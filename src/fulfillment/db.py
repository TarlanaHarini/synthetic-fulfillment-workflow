"""SQLite connection and schema initialization."""
from pathlib import Path
import sqlite3
PACKAGE_DIR=Path(__file__).resolve().parent
DEFAULT_DATABASE=PACKAGE_DIR.parent.parent/"fulfillment.sqlite3"
SCHEMA_PATH=PACKAGE_DIR/"schema.sql"
def connect(database=DEFAULT_DATABASE):
    conn=sqlite3.connect(str(database))
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
def initialize_database(database=DEFAULT_DATABASE):
    database = Path(database)

    if database.exists():
        database.unlink()

    conn = connect(database)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    return conn
def foreign_key_violations(conn):
    return list(conn.execute("PRAGMA foreign_key_check"))
