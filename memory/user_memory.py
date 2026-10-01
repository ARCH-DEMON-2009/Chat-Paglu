import json
from typing import Any, Dict, List


def extract_memories(message: str, conversation_context: List[str] | None = None) -> List[str]:
    text = (message or '').strip()
    if not text:
        return []
    memories: List[str] = []
    if 'favorite game' in text.lower() or 'love minecraft' in text.lower() or 'minecraft' in text.lower():
        memories.append('favorite game: Minecraft')
    if 'like' in text.lower() and 'i' in text.lower():
        memories.append(text)
    if conversation_context:
        memories.extend([item for item in conversation_context if len(item) > 5][:3])
    return memories


def remember_user_fact(memory_store, user_id: str, fact_key: str, fact_value: str) -> None:
    memory_store.record_user_fact(user_id, fact_key, fact_value)


def remember_user_profile(memory_store, user_id: str, user_data: Dict[str, Any]) -> None:
    memory_store.upsert_user(user_id, user_data.get('name'), user_data.get('nickname'))
