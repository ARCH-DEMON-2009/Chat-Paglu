from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple


class ConversationContext:
    def __init__(self, max_items: int = 30):
        self.max_items = max_items
        self.history: Dict[str, Deque[str]] = defaultdict(deque)
        self.group_history: Dict[str, Deque[str]] = defaultdict(deque)

    def add_user_message(self, user_id: str, text: str) -> None:
        self.history[str(user_id)].append(text)
        if len(self.history[str(user_id)]) > self.max_items:
            self.history[str(user_id)].popleft()

    def add_group_message(self, chat_id: str, text: str) -> None:
        self.group_history[str(chat_id)].append(text)
        if len(self.group_history[str(chat_id)]) > self.max_items:
            self.group_history[str(chat_id)].popleft()

    def get_user_messages(self, user_id: str) -> List[str]:
        return list(self.history.get(str(user_id), []))

    def get_group_messages(self, chat_id: str) -> List[str]:
        return list(self.group_history.get(str(chat_id), []))


def build_context_snapshot(user_id: str, chat_id: str, context: ConversationContext) -> Dict[str, object]:
    return {
        "user_id": str(user_id),
        "chat_id": str(chat_id),
        "recent_messages": context.get_user_messages(user_id),
        "recent_group_messages": context.get_group_messages(chat_id),
    }
