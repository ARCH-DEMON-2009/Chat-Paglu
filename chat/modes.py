from typing import Dict


class ChatMode:
    NORMAL = "normal"
    LOVE = "love"
    ABUSE = "abuse"


_USER_MODES: Dict[str, str] = {}


def get_user_mode(user_id: str) -> str:
    return _USER_MODES.get(str(user_id), ChatMode.NORMAL)


def set_user_mode(user_id: str, mode: str) -> str:
    normalized = mode.lower() if isinstance(mode, str) else ChatMode.NORMAL
    if normalized not in {ChatMode.NORMAL, ChatMode.LOVE, ChatMode.ABUSE}:
        normalized = ChatMode.NORMAL
    _USER_MODES[str(user_id)] = normalized
    return normalized


def clear_user_mode(user_id: str) -> str:
    _USER_MODES.pop(str(user_id), None)
    return ChatMode.NORMAL
