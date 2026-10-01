import asyncio
import logging
import os
import random
import re
import time
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ai_chat import (
    get_abuse_response,
    get_ai_response,
    get_group_response,
    get_lover_response,
    get_random_compliment,
    get_random_dare,
    get_random_fortune,
    get_random_joke,
    get_random_quote,
    get_random_truth,
)
from character.profile import build_character_prompt, load_character_profile, save_character_profile
from chat.context import ConversationContext
from chat.modes import ChatMode, clear_user_mode, get_user_mode, set_user_mode
from chat.participation import should_participate
from chat.typing import get_typing_delay, send_typing
from config.settings import load_settings
from memory.manager import MemoryStore
from memory.user_memory import extract_memories
from vision.analyzer import VisionService

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

settings = load_settings()
memory_store = MemoryStore(settings.database_url)
vision_service = VisionService(enabled=settings.vision_enabled)
conversation_context = ConversationContext(max_items=settings.max_group_context)
last_bot_response: dict[str, float] = {}
cooldowns: dict[str, float] = {}


class HandlerMap(dict):
    def __iter__(self):
        return iter(self.values())


def normalize_user_id(value: object) -> str:
    return str(value).strip()


def is_admin(user_id: object) -> bool:
    admin_ids = {str(item).strip() for item in settings.admin_ids}
    return normalize_user_id(user_id) in admin_ids


async def _send_normal_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, *, reply_to_message_id: Optional[int] = None):
    if not text or not text.strip():
        return
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    delay = get_typing_delay(len(text), settings.typing_delay_min, settings.typing_delay_max)
    try:
        await send_typing(context, chat_id, delay)
    except Exception as exc:
        logger.info('Typing indicator unavailable (%s).', type(exc).__name__)
    if reply_to_message_id:
        await update.message.reply_text(text, reply_to_message_id=reply_to_message_id)
    else:
        await update.message.reply_text(text)
    now = time.time()
    last_bot_response[user_id] = now
    cooldowns[str(chat_id)] = now


def _remember_if_needed(user_id: str, message: str) -> None:
    if not settings.memory_enabled:
        return
    lower = message.lower()
    if 'remember' in lower and ('like' in lower or 'love' in lower or 'favorite' in lower):
        fact = message.replace('remember', '', 1).strip()
        if fact:
            memory_store.record_user_fact(user_id, 'remembered_fact', fact)
    if 'favorite game' in lower or 'i like' in lower or 'i love' in lower:
        fact = message.strip()
        if fact:
            memory_store.record_user_fact(user_id, 'preference', fact)


def _get_memory_answer(user_id: str, message: str) -> Optional[str]:
    if not settings.memory_enabled:
        return None
    lower = message.lower()
    if 'what game do i like' in lower or 'what game i like' in lower:
        facts = memory_store.get_user_facts(user_id)
        for fact in facts:
            if 'minecraft' in fact.lower():
                return 'Minecraft 😭'
        return 'I don’t remember your favorite game yet — tell me and I’ll keep it.'
    if 'what do i like' in lower:
        facts = memory_store.get_user_facts(user_id)
        if facts:
            return facts[-1]
    if 'are you a real person' in lower or 'are you a real human' in lower:
        return 'I’m Aisha, a fictional AI girl character in this chat — not a real person, but I can still be natural and fun with you.'
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if update.effective_chat.type == 'private':
        if settings.memory_enabled:
            memory_store.upsert_user(user_id, update.effective_user.first_name, update.effective_user.username)
        await update.message.reply_text(
            'Heyy, I’m Aisha 😊 I’m here to chat, joke, answer questions, and hang out in your group. Use /help to see what I can do.'
        )
    else:
        await update.message.reply_text('Aisha is online and ready to join the group chat. 😌')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        'Aisha commands:\n\n'
        '/help - Show this menu\n'
        '/love - turn on affectionate mode\n'
        '/love off - disable romance mode\n'
        '/abuse - playful roast mode\n'
        '/abuse off - disable roast mode\n'
        '/stats - bot stats\n'
        '/reload - reload config\n'
        '/memory - view recent memory\n'
        '/clear_memory - clear your memory\n'
        '/participation - toggle group participation\n'
        '/cooldown - set cooldown\n'
        '/vision - toggle image analysis\n'
        '/admin - admin panel\n'
        '/joke /quote /tip /compliment /fortune /dare /truth'
    )
    await update.message.reply_text(help_text)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied. Only the configured admin can use this command.')
        return
    panel = (
        'Admin controls:\n'
        '/stats\n'
        '/reload\n'
        '/setname NAME\n'
        '/setprompt TEXT\n'
        '/memory [user_id]\n'
        '/clear_memory [user_id]\n'
        '/participation\n'
        '/cooldown SECONDS\n'
        '/vision on/off\n'
        '/love /abuse\n'
        '/status'
    )
    await update.message.reply_text(panel)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    stats = memory_store.get_stats()
    profile = load_character_profile()
    info = (
        f'Bot status: online\n'
        f'Name: {profile.get("name", "Aisha")}\n'
        f'Memory users: {stats.get("users", 0)}\n'
        f'Group contexts: {stats.get("groups", 0)}\n'
        f'Vision: {str(settings.vision_enabled).lower()}\n'
        f'Participation: {str(settings.group_participation_enabled).lower()}\n'
        f'Per-user cooldown: {settings.per_user_cooldown_seconds}s'
    )
    await update.message.reply_text(info)


async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    global settings, vision_service
    settings = load_settings()
    vision_service = VisionService(enabled=settings.vision_enabled)
    await update.message.reply_text('Config reloaded and settings updated.')


async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    if not context.args:
        await update.message.reply_text('Usage: /setname Aisha')
        return
    profile = load_character_profile()
    profile['name'] = ' '.join(context.args)
    profile['nickname'] = profile['name']
    save_character_profile(profile)
    await update.message.reply_text(f'Character name updated to {profile["name"]}.')


async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    if not context.args:
        await update.message.reply_text('Usage: /setprompt Your custom prompt text')
        return
    prompt = ' '.join(context.args)
    profile = load_character_profile()
    profile['custom_prompt'] = prompt
    save_character_profile(profile)
    await update.message.reply_text('Custom prompt updated.')


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    target = context.args[0] if context.args else str(update.effective_user.id)
    facts = memory_store.get_user_facts(target)
    if not facts:
        await update.message.reply_text('No stored memory found for that user.')
        return
    await update.message.reply_text('Stored memory:\n' + '\n'.join(facts[-10:]))


async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    target = context.args[0] if context.args else str(update.effective_user.id)
    memory_store.clear_user_memory(target)
    await update.message.reply_text(f'Memory cleared for {target}.')


async def participation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    settings.group_participation_enabled = not settings.group_participation_enabled
    await update.message.reply_text(f'Group participation is now {str(settings.group_participation_enabled).lower()}.')


async def cooldown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    if not context.args:
        await update.message.reply_text('Usage: /cooldown 15')
        return
    try:
        value = int(context.args[0])
        settings.per_user_cooldown_seconds = value
        await update.message.reply_text(f'Cooldown updated to {value} seconds.')
    except ValueError:
        await update.message.reply_text('Invalid cooldown value. Use a number.')


async def vision_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text('Permission denied.')
        return
    if not context.args:
        await update.message.reply_text('Usage: /vision on|off')
        return
    state = context.args[0].lower()
    settings.vision_enabled = state in {'on', 'true', '1'}
    vision_service.enabled = settings.vision_enabled
    await update.message.reply_text(f'Vision is now {str(settings.vision_enabled).lower()}.')


async def love_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_type = update.effective_chat.type
    args = [arg.strip() for arg in (context.args or []) if arg and arg.strip()]
    mention = next((arg for arg in args if re.fullmatch(r'@[A-Za-z0-9_]{5,32}', arg)), None)
    toggle_args = [arg for arg in args if not arg.startswith('@')]
    if toggle_args and toggle_args[0].lower() in {'off', 'disable', 'false'}:
        clear_user_mode(user_id)
        await update.message.reply_text('Love mode is off. Back to normal chat.')
        return
    if mention and chat_type in {'group', 'supergroup'}:
        target_name = mention[1:]
        response = await asyncio.to_thread(
            get_lover_response,
            f'group:{update.effective_chat.id}:{target_name.lower()}',
            f'Write a short, respectful affectionate message addressed to {target_name}.',
            target_name,
        )
        await update.message.reply_text(f'{mention} {response}')
        return
    if chat_type in {'group', 'supergroup'} and not settings.love_mode_allowed_in_groups:
        await update.message.reply_text('Love mode is disabled in groups here.')
        return
    set_user_mode(user_id, ChatMode.LOVE)
    if mention:
        await update.message.reply_text(f'Love mode activated for {mention}. I’m feeling extra sweet and affectionate today ❤️')
        return
    await update.message.reply_text('Love mode activated. I’m feeling extra sweet and affectionate today ❤️')


async def abuse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if context.args and context.args[0].lower() in {'off', 'disable', 'false'}:
        clear_user_mode(user_id)
        await update.message.reply_text('Abuse mode is off. Back to normal. 😌')
        return
    set_user_mode(user_id, ChatMode.ABUSE)
    await update.message.reply_text('Abuse mode activated. I’ll keep it playful and teasing, not toxic 😏')


async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_joke())


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_quote())


async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_joke())


async def compliment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_compliment())


async def fortune_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_fortune())


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_dare())


async def truth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_random_truth())


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    if not text or text.startswith('/'):
        return
    user_id = str(update.effective_user.id)
    chat_type = update.effective_chat.type
    _remember_if_needed(user_id, text)

    memory_answer = _get_memory_answer(user_id, text)
    if memory_answer:
        await _send_normal_reply(update, context, memory_answer, reply_to_message_id=update.message.message_id)
        return

    if chat_type in {'group', 'supergroup'}:
        lower_text = text.lower()
        bot_username = (getattr(context.bot, 'username', None) or '').lower()
        direct_mention = bool(re.search(r'\b(aisha|naina)\b', lower_text)) or bool(bot_username and f'@{bot_username}' in lower_text)
        reply_to_bot = bool(update.message.reply_to_message and update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.id == context.bot.id)
        is_question = '?' in text
        explicit_trigger = direct_mention or reply_to_bot or is_question
        should_reply = explicit_trigger
        if not should_reply and settings.group_participation_enabled:
            now = time.time()
            user_cooldown_passed = now - last_bot_response.get(user_id, 0) >= settings.per_user_cooldown_seconds
            group_cooldown_passed = now - cooldowns.get(str(update.effective_chat.id), 0) >= settings.global_cooldown_seconds
            should_reply = user_cooldown_passed and group_cooldown_passed and should_participate(
                context,
                probability=settings.group_response_probability,
            )
        if not should_reply:
            return
        user_name = update.effective_user.first_name or update.effective_user.username or 'User'
        mode = get_user_mode(user_id)
        if mode == ChatMode.LOVE:
            response = await asyncio.to_thread(get_lover_response, user_id, text, user_name)
        elif mode == ChatMode.ABUSE:
            response = await asyncio.to_thread(get_abuse_response, user_id, text, user_name)
        else:
            response = await asyncio.to_thread(get_group_response, str(update.effective_chat.id), user_name, text)
        await _send_normal_reply(update, context, response, reply_to_message_id=update.message.message_id if reply_to_bot or direct_mention else None)
        return

    mode = get_user_mode(user_id)
    if mode == ChatMode.LOVE:
        response = await asyncio.to_thread(get_lover_response, user_id, text, update.effective_user.first_name or 'User')
    elif mode == ChatMode.ABUSE:
        response = await asyncio.to_thread(get_abuse_response, user_id, text, update.effective_user.first_name or 'User')
    else:
        response = await asyncio.to_thread(get_ai_response, user_id, text, update.effective_user.first_name or 'User')
    await _send_normal_reply(update, context, response, reply_to_message_id=update.message.message_id)


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not settings.vision_enabled:
        await update.message.reply_text('Image analysis is currently disabled.')
        return
    message = update.message
    caption = (message.caption or '').strip()
    try:
        photo = message.photo[-1]
        telegram_file = await photo.get_file()
        image_bytes = bytes(await telegram_file.download_as_bytearray())
    except Exception as exc:
        logger.warning('Could not download a Telegram photo (%s).', type(exc).__name__)
        await message.reply_text('I couldn’t download that image. Please try sending it again.')
        return
    answer = await asyncio.to_thread(
        vision_service.answer_image_question,
        caption or 'Describe this image and read any visible text.',
        image_bytes,
        'image/jpeg',
    )
    await _send_normal_reply(update, context, answer, reply_to_message_id=message.message_id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception('Unhandled bot error.', exc_info=context.error)


def register_commands(application: Application) -> None:
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('admin', admin))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('status', stats))
    application.add_handler(CommandHandler('reload', reload_config))
    application.add_handler(CommandHandler('setname', set_name))
    application.add_handler(CommandHandler('setprompt', set_prompt))
    application.add_handler(CommandHandler('memory', memory_command))
    application.add_handler(CommandHandler('clear_memory', clear_memory))
    application.add_handler(CommandHandler('participation', participation_command))
    application.add_handler(CommandHandler('cooldown', cooldown_command))
    application.add_handler(CommandHandler('vision', vision_command))
    application.add_handler(CommandHandler('love', love_command))
    application.add_handler(CommandHandler('lover', love_command))
    application.add_handler(CommandHandler('abuse', abuse_command))
    application.add_handler(CommandHandler('joke', joke_command))
    application.add_handler(CommandHandler('quote', quote_command))
    application.add_handler(CommandHandler('tip', tip_command))
    application.add_handler(CommandHandler('compliment', compliment_command))
    application.add_handler(CommandHandler('fortune', fortune_command))
    application.add_handler(CommandHandler('dare', dare_command))
    application.add_handler(CommandHandler('truth', truth_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_error_handler(error_handler)


def build_application(token: Optional[str] = None) -> Application:
    bot_token = token or settings.telegram_bot_token or 'test-token'
    application = Application.builder().token(bot_token).build()
    register_commands(application)
    application.handlers = HandlerMap(application.handlers)
    return application


def main() -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit('TELEGRAM_BOT_TOKEN is missing. Add it to your environment or .env file.')
    app = build_application(token)
    logger.info('Aisha bot started successfully.')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
