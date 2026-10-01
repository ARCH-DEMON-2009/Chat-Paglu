import os

from config.settings import load_settings
from memory.manager import MemoryStore
from chat.modes import ChatMode, get_user_mode, set_user_mode, clear_user_mode
from main import register_commands, build_application


def test_settings_loads_defaults():
    settings = load_settings()
    assert settings is not None
    assert isinstance(settings.admin_ids, set)
    assert settings.group_response_probability >= 0


def test_memory_store_remembers_and_retrieves():
    store = MemoryStore(path=':memory:')
    user_id = '123'
    store.record_user_fact(user_id, 'favorite game', 'Minecraft')
    facts = store.get_user_facts(user_id)
    assert any('Minecraft' in item for item in facts)


def test_chat_modes_are_registered():
    assert ChatMode.NORMAL == 'normal'
    assert ChatMode.LOVE == 'love'
    assert ChatMode.ABUSE == 'abuse'
    set_user_mode('42', ChatMode.LOVE)
    assert get_user_mode('42') == ChatMode.LOVE
    clear_user_mode('42')
    assert get_user_mode('42') == ChatMode.NORMAL


def test_command_registration_includes_required_commands():
    app = build_application('test-token')
    names = set()
    for handler in app.handlers:
        for h in handler:
            if hasattr(h, 'commands'):
                names.update(h.commands)
    required = {
        'start', 'admin', 'stats', 'reload', 'setname', 'setprompt', 'memory',
        'clear_memory', 'participation', 'cooldown', 'vision', 'love', 'abuse',
        'lover', 'help'
    }
    assert required.issubset(names)


def test_image_question_answer_is_safe():
    from vision.analyzer import VisionService
    service = VisionService()
    answer = service.answer_image_question('What is 25 * 16?')
    assert '400' in answer
