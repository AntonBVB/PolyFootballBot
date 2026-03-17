import sqlite3
from pathlib import Path


def init_sqlite(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.commit()
