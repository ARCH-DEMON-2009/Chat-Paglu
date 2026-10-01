import json
import os
from typing import Any, Dict, List

from memory.database import DatabaseManager


class MemoryStore:
    def __init__(self, path: str | None = None):
        self.db = DatabaseManager(path)

    def upsert_user(self, user_id: str, name: str | None = None, nickname: str | None = None) -> None:
        with self.db.get_connection() as conn:
            existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                updates = []
                values = []
                if name is not None:
                    updates.append("name = ?")
                    values.append(name)
                if nickname is not None:
                    updates.append("nickname = ?")
                    values.append(nickname)
                if updates:
                    values.append(user_id)
                    conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", tuple(values))
                return
            conn.execute(
                "INSERT INTO users (user_id, name, nickname, preferences, interests, facts, interaction_count, last_seen, relationship, mode) VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, 'group_member', 'normal')",
                (user_id, name or '', nickname or '', '[]', '[]', '[]'),
            )
            conn.commit()

    def record_user_fact(self, user_id: str, key: str, value: str) -> None:
        self.upsert_user(user_id)
        with self.db.get_connection() as conn:
            existing = conn.execute("SELECT facts FROM users WHERE user_id = ?", (user_id,)).fetchone()
            facts = json.loads(existing["facts"]) if existing and existing["facts"] else []
            facts.append({"key": key, "value": value})
            conn.execute("UPDATE users SET facts = ? WHERE user_id = ?", (json.dumps(facts[-50:]), user_id))
            conn.commit()

    def get_user_facts(self, user_id: str) -> List[str]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT facts FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row or not row["facts"]:
                return []
            facts = json.loads(row["facts"])
            return [f"{item.get('key', 'fact')}: {item.get('value', '')}" for item in facts]

    def clear_user_memory(self, user_id: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute("UPDATE users SET facts = '[]', preferences='[]', interests='[]' WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            conn.commit()

    def record_group_message(self, chat_id: str, user_id: str, user_name: str, text: str, reply_to: str | None = None) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO group_context (chat_id, user_id, user_name, text, reply_to) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, user_name, text, reply_to),
            )
            conn.commit()

    def get_group_context(self, chat_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT user_name, text, reply_to, timestamp FROM group_context WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
                (chat_id, limit),
            ).fetchall()
            return [dict(row) for row in rows[::-1]]

    def get_stats(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            group_count = conn.execute("SELECT COUNT(DISTINCT chat_id) FROM group_context").fetchone()[0]
            return {
                "users": user_count,
                "memories": memory_count,
                "groups": group_count,
            }


memory_store = MemoryStore(os.getenv("DATABASE_URL", "chatpaglu.db"))
