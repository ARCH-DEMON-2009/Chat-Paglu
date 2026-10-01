import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chatpaglu.db")


def get_database_path(path: Optional[str] = None) -> str:
    if path is not None:
        return path
    if os.getenv("USE_SUPABASE", "false").lower() in {"1", "true", "yes", "on"}:
        return os.getenv("DATABASE_URL", DEFAULT_DB_PATH)
    return os.getenv("DATABASE_URL", DEFAULT_DB_PATH) if os.getenv("DATABASE_URL", "").startswith(("sqlite://", "sqlite:///", ":memory:")) else DEFAULT_DB_PATH


class DatabaseManager:
    def __init__(self, path: Optional[str] = None):
        self.path = get_database_path(path)
        self._connection: sqlite3.Connection | None = None
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        if self.path == ':memory:':
            if self._connection is None:
                self._connection = sqlite3.connect(self.path, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
            return self._connection
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    nickname TEXT,
                    preferences TEXT,
                    interests TEXT,
                    facts TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    last_seen TEXT,
                    relationship TEXT,
                    mode TEXT DEFAULT 'normal'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    key TEXT,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'user'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS group_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    text TEXT,
                    reply_to TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    text TEXT,
                    message_type TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS character_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()


def init_database(path: Optional[str] = None) -> DatabaseManager:
    return DatabaseManager(path)
