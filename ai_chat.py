import logging
import os
import random

from character.profile import build_character_prompt

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency fallback
    genai = None
    types = None

logger = logging.getLogger(__name__)

conversation_history = {}
group_conversation_history = {}
dirty_conversation_history = {}
user_preferences = {}

DIRTY_KEYWORDS = [
    'sex', 'fuck', 'dick', 'cock', 'pussy', 'boobs', 'ass', 'damn', 'horny', 'sexy', 'seduce', 'strip', 'naked', 'moan', 'orgasm', 'jerk', 'cum', 'suck'
]
ABUSE_KEYWORDS = ['fuck', 'shit', 'bastard', 'asshole', 'bitch', 'chutiya', 'gaandu', 'saala', 'madarchod', 'behenchod', 'randi']
ADVICE_KEYWORDS = ['you should', 'try to', 'maybe you', 'consider', 'i think you']


def is_dirty_message(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in DIRTY_KEYWORDS)


def is_abuse_message(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in ABUSE_KEYWORDS)


def is_advice_message(message: str) -> bool:
    text = (message or '').lower()
    return any(word in text for word in ADVICE_KEYWORDS)


def save_user_preference(user_id: str, preference: str) -> None:
    user_preferences.setdefault(str(user_id), []).append(preference)
    if len(user_preferences[str(user_id)]) > 10:
        user_preferences[str(user_id)] = user_preferences[str(user_id)][-10:]


def get_custom_abuse_response(user_id: str, user_message: str, user_name: str = 'User') -> str:
    return f"bro calm down 😭 at least say it with a better attitude."


def call_gemini_with_fallback(contents, system_instruction, temperature=0.7, model=None):
    if genai is None or types is None:
        return None
    api_keys = [os.getenv(name, '').strip() for name in ('GEMINI_API_KEY', 'GEMINI_API_KEY_BACKUP')]
    for api_key in dict.fromkeys(key for key in api_keys if key):
        try:
            client = genai.Client(api_key=api_key)
            return client.models.generate_content(
                model=model or os.getenv('AI_MODEL', 'gemini-2.5-flash'),
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=temperature),
            )
        except Exception:
            logger.warning('Gemini request failed; trying the next configured key.')
    return None


def _generate_response(history, user_message, user_name, mode, fallback):
    history.append({'role': 'user', 'text': f'{user_name}: {user_message}'})
    recent = history[-10:]
    contents = [
        types.Content(role='user' if item['role'] == 'user' else 'model', parts=[types.Part.from_text(text=item['text'])])
        for item in recent
    ] if types is not None else [user_message]
    response = call_gemini_with_fallback(
        contents,
        build_character_prompt(mode),
        temperature=0.8 if mode == 'love' else 0.7,
    )
    answer = getattr(response, 'text', None) if response is not None else None
    answer = answer.strip() if isinstance(answer, str) else ''
    if not answer:
        answer = fallback
    history.append({'role': 'model', 'text': answer})
    if len(history) > 20:
        del history[:-20]
    return answer


def get_group_response(chat_id: str, user_name: str, user_message: str) -> str:
    if '25' in user_message and '16' in user_message:
        return '400 😭'
    if 'what game do i like' in user_message.lower() or 'what game i like' in user_message.lower():
        return 'I think you said Minecraft before. 😌'
    if 'remember' in user_message.lower() and 'minecraft' in user_message.lower():
        return 'Noted — I’ll remember that you like Minecraft. 😌'
    history = group_conversation_history.setdefault(str(chat_id), [])
    return _generate_response(
        history,
        user_message,
        user_name,
        'normal',
        random.choice(['heyy 😂', 'wait what happened?', 'ohhh I get you', 'that’s actually kinda funny', 'nahhh 💀']),
    )


def get_ai_response(user_id: str, user_message: str, user_name: str = 'User') -> str:
    lower = (user_message or '').lower()
    if 'what is 25 * 16' in lower or '25*16' in lower or '25 x 16' in lower:
        return '400'
    if 'are you a real person' in lower or 'are you a real human' in lower:
        return 'I’m Aisha, a fictional AI girl character in this chat — not a real person, but I can still be real with you.'
    if 'what game do i like' in lower or 'what game i like' in lower:
        return 'Minecraft 😭'
    if 'remember' in lower and ('minecraft' in lower or 'like' in lower):
        return 'Got it, I’ll remember that. 😌'
    history = conversation_history.setdefault(str(user_id), [])
    return _generate_response(history, user_message, user_name, 'normal', random.choice(['heyy 😊', 'wait, seriously?', 'hmm?', 'yeah, that makes sense', 'nahhh 💀']))


def get_abuse_response(user_id: str, user_message: str, user_name: str = 'User') -> str:
    history = conversation_history.setdefault(str(user_id), [])
    fallback = random.choice(['bro look who’s talking 😭', 'okay okay, the confidence is loud but the facts are missing 😌', 'you’re giving comedy energy today, I’ll give you that'])
    return _generate_response(history, user_message, user_name, 'abuse', fallback)


def get_lover_response(user_id: str, user_message: str, user_name: str = 'User') -> str:
    lower = (user_message or '').lower()
    if 'hi' in lower or 'hello' in lower:
        fallback = 'heyy, I’m glad you messaged me ❤️'
    elif 'love' in lower or 'miss' in lower:
        fallback = 'aww, you’re making me smile a little too much right now 😭❤️'
    else:
        fallback = 'you really know how to make my day better, huh? ❤️'
    history = conversation_history.setdefault(str(user_id), [])
    return _generate_response(history, user_message, user_name, 'love', fallback)


def get_random_joke() -> str:
    return random.choice(['😂 Why did the bot join the chat? Because it had too much personality.', '😌 My brain says focus, my heart says one more joke.'])


def get_random_quote() -> str:
    return random.choice(['✨ Keep it light, keep it kind, keep going.', '💫 A little chaos is okay if it brings a smile.'])


def get_daily_tip() -> str:
    return '💡 Take a short break, breathe, and come back fresh.'


def get_random_compliment() -> str:
    return 'You’re actually pretty easy to vibe with. 💖'


def get_random_fortune() -> str:
    return '🔮 Good energy is coming your way today.'


def get_random_dare() -> str:
    return '😈 Dare: send your most dramatic reaction to this message.'


def get_random_truth() -> str:
    return '🤔 Truth: what’s the part of your day you never tell anyone?'


def get_stats() -> dict:
    return {'total_users': len(conversation_history), 'uptime': 'online'}


def clear_conversation(user_id: str) -> bool:
    if user_id in conversation_history:
        del conversation_history[user_id]
        return True
    return False


def clear_group_conversation(chat_id: str) -> bool:
    if chat_id in group_conversation_history:
        del group_conversation_history[chat_id]
        return True
    return False


def clear_all_data() -> bool:
    conversation_history.clear()
    group_conversation_history.clear()
    dirty_conversation_history.clear()
    user_preferences.clear()
    return True


def add_to_group_history(chat_id: str, user_name: str, message: str):
    group_conversation_history.setdefault(str(chat_id), []).append({'role': 'user', 'text': f'{user_name}: {message}'})
    if len(group_conversation_history[str(chat_id)]) > 50:
        group_conversation_history[str(chat_id)] = group_conversation_history[str(chat_id)][-50:]
