import os
import sqlite3
from urllib.parse import unquote
from typing import Optional

try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:  # pragma: no cover - optional unless PostgreSQL is configured
    psycopg2 = None
    DictCursor = None

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chatpaglu.db")


def _is_postgres_url(value: str) -> bool:
    return value.lower().startswith(("postgres://", "postgresql://"))


def _looks_like_sqlite_path(value: Optional[str]) -> bool:
    if value is None:
        return False
    value = str(value).strip()
    if not value or value == ':memory:':
        return True
    lowered = value.lower()
    if lowered.startswith(('sqlite://', 'sqlite:///')):
        return True
    if lowered.startswith(('postgres://', 'postgresql://', 'mysql://', 'mariadb://')):
        return False
    return value.endswith(('.db', '.sqlite', '.sqlite3')) or value.startswith(('.', '/', os.sep)) or '/' in value or '\\' in value


def get_database_path(path: Optional[str] = None) -> str:
    use_supabase = os.getenv("USE_SUPABASE", "false").strip().lower() in {"1", "true", "yes", "on"}
    if path is not None:
        value = str(path).strip()
        if _is_postgres_url(value):
            return value if use_supabase else DEFAULT_DB_PATH
        if value.lower().startswith("sqlite://"):
            if value.startswith("sqlite:////"):
                return unquote(value[len("sqlite:///"):])
            if value.startswith("sqlite:///"):
                return unquote(value[len("sqlite:///"):])
            return unquote(value[len("sqlite://"):])
        if _looks_like_sqlite_path(path):
            return value
        return DEFAULT_DB_PATH
    database_url = os.getenv("DATABASE_URL", "").strip()
    if _is_postgres_url(database_url):
        return database_url if use_supabase else DEFAULT_DB_PATH
    if use_supabase:
        raise ValueError("USE_SUPABASE is enabled but DATABASE_URL is not a PostgreSQL connection URL.")
    if database_url.lower().startswith("sqlite://"):
        return get_database_path(database_url)
    if database_url and _looks_like_sqlite_path(database_url):
        return database_url
    return DEFAULT_DB_PATH


class _PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()

    def execute(self, statement, parameters=()):
        cursor = self.connection.cursor(cursor_factory=DictCursor)
        cursor.execute(statement.replace("?", "%s"), parameters)
        return cursor

    def commit(self):
        self.connection.commit()


class DatabaseManager:
    def __init__(self, path: Optional[str] = None):
        self.path = get_database_path(path)
        self.is_postgres = _is_postgres_url(self.path)
        self._connection: sqlite3.Connection | None = None
        if not self.is_postgres:
            self.init_db()

    def get_connection(self):
        if self.is_postgres:
            if psycopg2 is None:
                raise RuntimeError("PostgreSQL is configured but psycopg2 is not installed. Install the project dependencies.")
            return _PostgresConnection(psycopg2.connect(self.path, sslmode="require"))
        if self.path == ':memory:':
            if self._connection is None:
                self._connection = sqlite3.connect(self.path, check_same_thread=False)
                self._connection.row_factory = sqlite3.Row
            return self._connection
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        if self.is_postgres:
            return
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
