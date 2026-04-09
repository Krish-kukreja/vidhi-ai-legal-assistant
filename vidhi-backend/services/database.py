import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "vidhi.db")

def init_db():
    """Initializes the SQLite database with required tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS matters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS matter_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matter_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(matter_id) REFERENCES matters(id)
            )
        """)
        db.commit()
    logger.info("Database initialized successfully.")

@contextmanager
def get_db():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize upon import
init_db()
