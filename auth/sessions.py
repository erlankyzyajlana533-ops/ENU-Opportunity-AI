
# ==========================================
# ENU OPPORTUNITY AI
# DATABASE SESSION MANAGEMENT
# ==========================================

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "enu_opportunity.db"
)

SESSION_LIFETIME = 3600


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_sessions_table():
    """Сессиялар кестесін құру."""

    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_user_sessions_user_id
            ON user_sessions(user_id)
        """)


def hash_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def utc_now():
    return datetime.now(timezone.utc)


def create_session(user):
    """Тіркелген пайдаланушыға сессия жасау."""

    create_sessions_table()

    if not user or not user.get("id"):
        raise ValueError("Пайдаланушы ID қажет")

    token = secrets.token_urlsafe(32)

    now = utc_now()
    expires = now + timedelta(
        seconds=SESSION_LIFETIME
    )

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO user_sessions (
                token_hash,
                user_id,
                expires_at,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            hash_token(token),
            user["id"],
            expires.isoformat(),
            now.isoformat()
        ))

    return token


def get_session(session_id):
    """Сессияның жарамдылығын тексеру."""

    if not session_id:
        return None

    create_sessions_table()

    with connect_db() as conn:
        row = conn.execute("""
            SELECT
                u.id,
                u.full_name,
                u.email,
                u.role,
                u.profile_id,
                u.is_active,
                s.expires_at
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
        """, (hash_token(session_id),)).fetchone()

        if row is None:
            return None

        expires = datetime.fromisoformat(
            row["expires_at"]
        )

        if utc_now() >= expires:
            conn.execute("""
                DELETE FROM user_sessions
                WHERE token_hash = ?
            """, (hash_token(session_id),))
            return None

        if not row["is_active"]:
            return None

        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
            "profile_id": row["profile_id"]
        }


def delete_session(session_id):
    """Жүйеден шығу."""

    if not session_id:
        return

    create_sessions_table()

    with connect_db() as conn:
        conn.execute("""
            DELETE FROM user_sessions
            WHERE token_hash = ?
        """, (hash_token(session_id),))


def delete_user_sessions(user_id):
    """Пайдаланушының барлық сессияларын тоқтату."""

    create_sessions_table()

    with connect_db() as conn:
        conn.execute("""
            DELETE FROM user_sessions
            WHERE user_id = ?
        """, (user_id,))
