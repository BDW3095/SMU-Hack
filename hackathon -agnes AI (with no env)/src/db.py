import sqlite3
import os
from datetime import datetime, timezone

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clicks.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clicks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  TEXT,
                product_name TEXT,
                category    TEXT,
                product_url TEXT,
                session_id  TEXT,
                timestamp   TEXT
            )
        """)


def log_click(
    product_id: str,
    product_name: str,
    category: str,
    product_url: str,
    session_id: str,
) -> None:
    init_db()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO clicks
               (product_id, product_name, category, product_url, session_id, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                product_id,
                product_name,
                category,
                product_url,
                session_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_stats() -> dict:
    init_db()
    conn = _get_conn()
    try:
        total: int = conn.execute("SELECT COUNT(*) AS total FROM clicks").fetchone()["total"]

        by_category = [
            dict(r)
            for r in conn.execute(
                "SELECT category, COUNT(*) AS clicks FROM clicks"
                " GROUP BY category ORDER BY clicks DESC"
            ).fetchall()
        ]

        by_product = [
            dict(r)
            for r in conn.execute(
                "SELECT product_name, category, product_url, COUNT(*) AS clicks"
                " FROM clicks GROUP BY product_id ORDER BY clicks DESC LIMIT 20"
            ).fetchall()
        ]

        by_day = [
            dict(r)
            for r in conn.execute(
                "SELECT DATE(timestamp) AS day, COUNT(*) AS clicks"
                " FROM clicks GROUP BY day ORDER BY day DESC LIMIT 30"
            ).fetchall()
        ]

        recent = [
            dict(r)
            for r in conn.execute(
                "SELECT timestamp, product_name, category, product_url, session_id"
                " FROM clicks ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()
        ]
    finally:
        conn.close()

    return {
        "total": total,
        "by_category": by_category,
        "by_product": by_product,
        "by_day": by_day,
        "recent": recent,
    }
