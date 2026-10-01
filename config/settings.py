import os
from dataclasses import dataclass, field
from typing import Set

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_admin_ids(raw: str | None) -> Set[str]:
    if not raw:
        return set()
    ids = set()
    for item in raw.replace(";", ",").split(","):
        cleaned = str(item).strip()
        if cleaned:
            ids.add(cleaned)
    return ids


@dataclass
class BotSettings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_ids: Set[str] = field(default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_IDS")))
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini")
    ai_model: str = os.getenv("AI_MODEL", "gemini-2.5-flash")
    vision_model: str = os.getenv("VISION_MODEL", "gemini-2.5-flash")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "chatpaglu.db")
    use_supabase: bool = _as_bool(os.getenv("USE_SUPABASE"), False)
    group_response_mode: str = os.getenv("GROUP_RESPONSE_MODE", "smart")
    group_response_probability: float = _as_float(os.getenv("GROUP_RESPONSE_PROBABILITY"), 0.2)
    typing_delay_min: float = _as_float(os.getenv("TYPING_DELAY_MIN"), 0.5)
    typing_delay_max: float = _as_float(os.getenv("TYPING_DELAY_MAX"), 2.0)
    memory_enabled: bool = _as_bool(os.getenv("MEMORY_ENABLED"), True)
    vision_enabled: bool = _as_bool(os.getenv("VISION_ENABLED"), True)
    web_search_enabled: bool = _as_bool(os.getenv("WEB_SEARCH_ENABLED"), False)
    group_participation_enabled: bool = _as_bool(os.getenv("GROUP_PARTICIPATION_ENABLED"), True)
    love_mode_allowed_in_groups: bool = _as_bool(os.getenv("LOVE_MODE_ALLOWED_IN_GROUPS"), False)
    max_group_context: int = int(os.getenv("GROUP_CONTEXT_LIMIT", "30"))
    global_cooldown_seconds: int = int(os.getenv("GLOBAL_COOLDOWN_SECONDS", "15"))
    per_user_cooldown_seconds: int = int(os.getenv("PER_USER_COOLDOWN_SECONDS", "10"))


def load_settings() -> BotSettings:
    return BotSettings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        ai_provider=os.getenv("AI_PROVIDER", "gemini"),
        ai_model=os.getenv("AI_MODEL", "gemini-2.5-flash"),
        vision_model=os.getenv("VISION_MODEL", "gemini-2.5-flash"),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "chatpaglu.db"),
        use_supabase=_as_bool(os.getenv("USE_SUPABASE"), False),
        group_response_mode=os.getenv("GROUP_RESPONSE_MODE", "smart"),
        group_response_probability=_as_float(os.getenv("GROUP_RESPONSE_PROBABILITY"), 0.2),
        typing_delay_min=_as_float(os.getenv("TYPING_DELAY_MIN"), 0.5),
        typing_delay_max=_as_float(os.getenv("TYPING_DELAY_MAX"), 2.0),
        memory_enabled=_as_bool(os.getenv("MEMORY_ENABLED"), True),
        vision_enabled=_as_bool(os.getenv("VISION_ENABLED"), True),
        web_search_enabled=_as_bool(os.getenv("WEB_SEARCH_ENABLED"), False),
        group_participation_enabled=_as_bool(os.getenv("GROUP_PARTICIPATION_ENABLED"), True),
        love_mode_allowed_in_groups=_as_bool(os.getenv("LOVE_MODE_ALLOWED_IN_GROUPS"), False),
        max_group_context=int(os.getenv("GROUP_CONTEXT_LIMIT", "30")),
        global_cooldown_seconds=int(os.getenv("GLOBAL_COOLDOWN_SECONDS", "15")),
        per_user_cooldown_seconds=int(os.getenv("PER_USER_COOLDOWN_SECONDS", "10")),
    )
