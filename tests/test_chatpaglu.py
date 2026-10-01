import asyncio
import os
from types import SimpleNamespace

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


def test_ai_response_uses_configured_provider(monkeypatch):
    import ai_chat

    class Response:
        text = 'A live-model response.'

    monkeypatch.setattr(ai_chat, 'call_gemini_with_fallback', lambda *args, **kwargs: Response())

    assert ai_chat.get_ai_response('test-user', 'Tell me something specific.') == 'A live-model response.'


def test_gemini_client_uses_configured_key_and_model(monkeypatch):
    import ai_chat

    captured = {}

    class Models:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text='Provider response.')

    def client_factory(api_key):
        captured['api_key'] = api_key
        return SimpleNamespace(models=Models())

    monkeypatch.setattr(ai_chat, 'genai', SimpleNamespace(Client=client_factory))
    monkeypatch.setattr(ai_chat, 'types', SimpleNamespace(GenerateContentConfig=lambda **kwargs: kwargs))
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setenv('AI_MODEL', 'test-model')

    response = ai_chat.call_gemini_with_fallback(['hello'], 'system prompt')

    assert response.text == 'Provider response.'
    assert captured['api_key'] == 'test-key'
    assert captured['model'] == 'test-model'
    assert captured['config']['system_instruction'] == 'system prompt'


def test_group_participation_toggle_blocks_only_unsolicited_replies(monkeypatch):
    import main

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7, first_name='Sam', username='sam'),
        effective_chat=SimpleNamespace(id=-100, type='group'),
        message=SimpleNamespace(text='hello everyone', message_id=12, reply_to_message=None),
    )
    context = SimpleNamespace(bot=SimpleNamespace(id=99, username='aisha_bot'))
    monkeypatch.setattr(main.settings, 'memory_enabled', False)
    monkeypatch.setattr(main.settings, 'group_participation_enabled', False)
    monkeypatch.setattr(main, 'should_participate', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('participation toggle ignored')))
    monkeypatch.setattr(main, '_send_normal_reply', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('unsolicited reply sent')))

    asyncio.run(main.handle_text_message(update, context))


def test_vision_sends_uploaded_bytes_to_provider(monkeypatch):
    import vision.analyzer as analyzer

    captured = {}

    class Response:
        text = 'The picture shows a blue bicycle.'

    def fake_provider(contents, *args, **kwargs):
        captured['contents'] = contents
        return Response()

    monkeypatch.setattr(analyzer, 'call_gemini_with_fallback', fake_provider)
    result = analyzer.VisionService().answer_image_question('Describe this.', b'image-bytes', 'image/png')

    assert result == 'The picture shows a blue bicycle.'
    assert captured['contents'][1].inline_data.data == b'image-bytes'


def test_vision_extracts_text_from_image_path(monkeypatch, tmp_path):
    import vision.analyzer as analyzer

    captured = {}

    class Response:
        text = '  EXIT   12  '

    def fake_provider(contents, *args, **kwargs):
        captured['contents'] = contents
        return Response()

    image_path = tmp_path / 'sign.png'
    image_path.write_bytes(b'image-data')
    monkeypatch.setattr(analyzer, 'call_gemini_with_fallback', fake_provider)

    assert analyzer.VisionService().extract_image_text(str(image_path)) == 'EXIT 12'
    assert captured['contents'][1].inline_data.data == b'image-data'


def test_database_urls_select_correct_backend(monkeypatch):
    from memory.database import DatabaseManager, get_database_path

    monkeypatch.setenv('USE_SUPABASE', 'true')
    assert get_database_path('postgresql://db.example/app') == 'postgresql://db.example/app'
    assert get_database_path('sqlite:///chat.db') == 'chat.db'
    assert get_database_path('sqlite:////tmp/chat.db') == '/tmp/chat.db'
    assert DatabaseManager('postgresql://db.example/app').is_postgres
    monkeypatch.setenv('USE_SUPABASE', 'false')
    assert get_database_path('postgresql://db.example/app').endswith('chatpaglu.db')


def test_group_participation_uses_configured_probability(monkeypatch):
    import chat.participation as participation

    monkeypatch.setattr(participation.random, 'random', lambda: 0.4)
    assert not participation.should_participate(None, probability=0.3)
    assert participation.should_participate(None, probability=0.5)
    assert participation.should_participate(None, direct_mention=True, probability=0)


def test_memory_setting_disables_reads_and_writes(monkeypatch):
    import main

    monkeypatch.setattr(main.settings, 'memory_enabled', False)
    monkeypatch.setattr(main.memory_store, 'record_user_fact', lambda *args: (_ for _ in ()).throw(AssertionError('memory write attempted')))

    main._remember_if_needed('user-1', 'I like Minecraft')
    assert main._get_memory_answer('user-1', 'what game do I like?') is None


def test_lover_mention_sends_addressed_message_in_group(monkeypatch):
    import main

    sent_messages = []

    async def reply_text(text):
        sent_messages.append(text)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_chat=SimpleNamespace(id=-100, type='group'),
        message=SimpleNamespace(reply_text=reply_text),
    )
    context = SimpleNamespace(args=['@CoffinWifi'])
    monkeypatch.setattr(main, 'get_lover_response', lambda *args: 'You make this chat brighter.')
    monkeypatch.setattr(main.settings, 'love_mode_allowed_in_groups', False)

    asyncio.run(main.love_command(update, context))

    assert sent_messages == ['@CoffinWifi You make this chat brighter.']


def test_photo_handler_downloads_and_forwards_image_bytes(monkeypatch):
    import main

    captured = {}
    sent_messages = []

    async def download_as_bytearray():
        return bytearray(b'photo-data')

    async def get_file():
        return SimpleNamespace(download_as_bytearray=download_as_bytearray)

    async def reply_text(text):
        sent_messages.append(text)

    async def send_reply(update, context, text, **kwargs):
        sent_messages.append(text)

    def answer_image_question(caption, image_bytes, mime_type):
        captured.update(caption=caption, image_bytes=image_bytes, mime_type=mime_type)
        return 'Image answer.'

    message = SimpleNamespace(
        caption='What is in this photo?',
        photo=[SimpleNamespace(get_file=get_file)],
        message_id=12,
        reply_text=reply_text,
    )
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100),
        effective_user=SimpleNamespace(id=7),
        message=message,
    )
    monkeypatch.setattr(main.settings, 'vision_enabled', True)
    monkeypatch.setattr(main.vision_service, 'answer_image_question', answer_image_question)
    monkeypatch.setattr(main, '_send_normal_reply', send_reply)

    asyncio.run(main.handle_photo_message(update, SimpleNamespace()))

    assert captured == {
        'caption': 'What is in this photo?',
        'image_bytes': b'photo-data',
        'mime_type': 'image/jpeg',
    }
    assert sent_messages == ['Image answer.']
