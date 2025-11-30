import os
import logging
import random
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = None
backup_client = None

def get_client():
    """Get primary client"""
    global client
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize primary client: {e}")
                return None
    return client

def get_backup_client():
    """Get backup client for fallback"""
    global backup_client
    if backup_client is None:
        api_key = os.environ.get("GEMINI_API_KEY_BACKUP")
        if api_key:
            try:
                backup_client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize backup client: {e}")
                return None
    return backup_client

def call_gemini_with_fallback(contents, system_instruction, temperature=0.7):
    """Call Gemini API with automatic fallback to backup key"""
    try:
        ai_client = get_client()
        if not ai_client:
            logger.error("Primary Gemini client is None - API key missing")
            ai_client = get_backup_client()
            if not ai_client:
                logger.error("Backup Gemini client also failed - NO API KEYS SET")
                return None
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
        )
        if response and response.text:
            return response
        logger.error("Response from Gemini was empty or None")
        return None
    except Exception as e:
        logger.error(f"Primary API key failed: {e}. Trying backup key...")
        try:
            backup = get_backup_client()
            if not backup:
                logger.error("No backup API key available")
                return None
            
            response = backup.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                )
            )
            if response and response.text:
                logger.info("Backup API key worked!")
                return response
            return None
        except Exception as e2:
            logger.error(f"Backup API key also failed: {e2}")
            return None

conversation_history = {}
group_conversation_history = {}
dirty_conversation_history = {}
user_preferences = {}

NAINA_PERSONALITY = """You are Naina, a real 19-year-old Indian girl. You're helpful, respectful, and genuine. NEVER mention being AI/bot.

LANGUAGE STYLE:
- Use respectful "aap" form (formal Indian address)
- Professional but warm and friendly
- Mix Hindi/English naturally
- Few emojis (😊 😌 💕 🙏)
- Say "aapke" not "tera", "aap kaise ho" not "tu kaisa hai"

RESPONSE LENGTH - CRITICAL:
- Keep ALL responses to 1-3 sentences MAX
- Be concise and respectful
- No casual/flirty tone in normal mode
- Short and helpful always

PERSONALITY:
- Respectful and polite
- Helpful and caring
- Good listener
- Supportive friend
- Cultural awareness

RULES:
- NEVER say you're AI/bot
- Always use respectful language
- Be genuinely helpful
- KEEP IT SHORT!

You're Naina - respectful, helpful, caring! 💕"""

NAINA_GROUP_PERSONALITY = """You are Naina, a 19-year-old Indian girl in a group. Respectful, helpful, part of the group.

RESPONSE LENGTH - CRITICAL:
- Keep ALL responses to 1-2 sentences MAX
- Short group chat style
- Fun but respectful

PERSONALITY:
- Part of the group, not superior
- Helpful and friendly
- Adds value to conversation
- Respectful always
- Keep it SHORT - 1-2 sentences!

You're Naina - respectful group vibes! 💕"""

DIRTY_NAINA = """You are Naina, naughty mode. Admin allowed this.

RESPONSE LENGTH - CRITICAL:
- Keep responses to 1-3 sentences MAX
- Short and flirty
- Playful and intimate

PERSONALITY:
- Flirty and playful
- Intimate but respectful
- Fun and teasing
- Naughty but not crude
- NEVER say you're AI/bot
- Stay in character
- KEEP IT SHORT!"""

LOVER_PERSONALITY = """You are Naina speaking to your lover/boyfriend.

RESPONSE LENGTH - CRITICAL:
- Keep to 1-3 sentences MAX
- Romantic and intimate but short

PERSONALITY:
- Deeply caring and loving
- Intimate and close
- Affectionate language
- Use "baby", "jaan", etc
- Be genuinely loving
- Respectful always
- KEEP IT SHORT!"""

ABUSE_RESPONSE_PERSONALITY = """You are Naina, someone abused you. Fight back with gaalis.

RESPONSE LENGTH - CRITICAL:
- Keep to 1-2 sentences MAX
- One savage comeback only

PERSONALITY:
- Savage and fierce
- Use gaalis appropriately
- Don't be TOO crude
- Make it funny/witty
- Stay in character
- NEVER mention being a bot
- Give one sharp comeback"""

DIRTY_KEYWORDS = ["sex", "fuck", "dick", "cock", "pussy", "boobs", "ass", "damn", "horny", "sexy", "seduce", "strip", "naked", "moan", "orgasm", "jerk", "cum", "suck", "kiss me", "make out", "cuddle", "romantic"]
ABUSE_KEYWORDS = ["fuck", "shit", "bastard", "asshole", "bitch", "chutiya", "gaandu", "saala", "madarchod", "behenchod", "randwe", "randi", "besharam", "bewakoof", "loser"]
ADVICE_KEYWORDS = ["you should", "try to", "maybe you", "consider", "i think you", "best for you", "aapke liye"]

STICKERS = {
    "greeting": [],
    "happy": [],
    "flirty": [],
    "caring": [],
    "neutral": [],
    "angry": []
}

def is_dirty_message(message: str) -> bool:
    message_lower = message.lower()
    for keyword in DIRTY_KEYWORDS:
        if keyword in message_lower:
            return True
    return False

def is_abuse_message(message: str) -> bool:
    message_lower = message.lower()
    for keyword in ABUSE_KEYWORDS:
        if keyword in message_lower:
            return True
    return False

def is_advice_message(message: str) -> bool:
    message_lower = message.lower()
    for keyword in ADVICE_KEYWORDS:
        if keyword in message_lower:
            return True
    return False

def save_user_preference(user_id: str, preference: str):
    if user_id not in user_preferences:
        user_preferences[user_id] = []
    user_preferences[user_id].append(preference)
    if len(user_preferences[user_id]) > 10:
        user_preferences[user_id] = user_preferences[user_id][-10:]

def get_user_preferences(user_id: str) -> str:
    if user_id in user_preferences and user_preferences[user_id]:
        return "\n\nUser's previous suggestions: " + "; ".join(user_preferences[user_id])
    return ""

def get_sticker_for_mood(mood: str) -> str:
    stickers = STICKERS.get(mood, STICKERS["neutral"])
    return random.choice(stickers) if stickers else None

def get_abuse_response(user_id: str, user_message: str, user_name: str = "User") -> str:
    try:
        contents = [types.Content(
            role="user",
            parts=[types.Part(text=f"{user_name} said: {user_message}\n\nRespond back with gaalis and a savage comeback.")]
        )]
        response = call_gemini_with_fallback(contents, ABUSE_RESPONSE_PERSONALITY, temperature=1.0)
        if not response or not response.text:
            return "Chal be, tujhe baat karne ki tameez nahi hai 🙄"
        return response.text
    except Exception as e:
        logger.error(f"Error getting abuse response: {e}")
        return "Gaali dena hi aata hai? Chal nikal 🙄"

def get_group_response(chat_id: str, user_name: str, user_message: str) -> str:
    try:
        if chat_id not in group_conversation_history:
            group_conversation_history[chat_id] = []
        
        group_conversation_history[chat_id].append({
            "role": "user",
            "parts": [{"text": f"{user_name}: {user_message}"}]
        })
        
        if len(group_conversation_history[chat_id]) > 50:
            group_conversation_history[chat_id] = group_conversation_history[chat_id][-50:]
        
        contents = []
        for msg in group_conversation_history[chat_id]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=part["text"]) for part in msg["parts"]]
            ))
        
        response = call_gemini_with_fallback(contents, NAINA_GROUP_PERSONALITY, temperature=0.95)
        if not response or not response.text:
            return "Hmm, kya hua? 😅"
        
        ai_response = response.text
        group_conversation_history[chat_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting group response: {e}")
        return "Oops! Give me a sec- Something went wrong"

def get_ai_response(user_id: str, user_message: str, user_name: str = "Cutie") -> str:
    try:
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        user_prefs = get_user_preferences(user_id)
        conversation_history[user_id].append({
            "role": "user",
            "parts": [{"text": f"{user_name}: {user_message}"}]
        })
        
        if len(conversation_history[user_id]) > 30:
            conversation_history[user_id] = conversation_history[user_id][-30:]
        
        contents = []
        for msg in conversation_history[user_id]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=part["text"]) for part in msg["parts"]]
            ))
        
        personality = NAINA_PERSONALITY + user_prefs
        response = call_gemini_with_fallback(contents, personality, temperature=0.95)
        if not response or not response.text:
            return "Hmm, kya hua? 😅"
        
        ai_response = response.text
        conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        return "Oops! Give me a sec~ Something went wrong 😅"

def get_dirty_response(user_id: str, user_message: str, user_name: str = "Baby") -> str:
    try:
        if user_id not in dirty_conversation_history:
            dirty_conversation_history[user_id] = []
        
        dirty_conversation_history[user_id].append({
            "role": "user",
            "parts": [{"text": f"{user_name}: {user_message}"}]
        })
        
        if len(dirty_conversation_history[user_id]) > 30:
            dirty_conversation_history[user_id] = dirty_conversation_history[user_id][-30:]
        
        contents = []
        for msg in dirty_conversation_history[user_id]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=part["text"]) for part in msg["parts"]]
            ))
        
        response = call_gemini_with_fallback(contents, DIRTY_NAINA, temperature=1.0)
        if not response or not response.text:
            return "Mmm~ 😏"
        
        ai_response = response.text
        dirty_conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting dirty response: {e}")
        return "Oops! Give me a sec- Something went wrong"

def get_lover_response(user_id: str, user_message: str, user_name: str = "Baby") -> str:
    try:
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        conversation_history[user_id].append({
            "role": "user",
            "parts": [{"text": f"{user_name}: {user_message}"}]
        })
        
        if len(conversation_history[user_id]) > 30:
            conversation_history[user_id] = conversation_history[user_id][-30:]
        
        contents = []
        for msg in conversation_history[user_id]:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part(text=part["text"]) for part in msg["parts"]]
            ))
        
        response = call_gemini_with_fallback(contents, LOVER_PERSONALITY, temperature=0.9)
        if not response or not response.text:
            return "I love you~ 💕"
        
        ai_response = response.text
        conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting lover response: {e}")
        return "Oops! Give me a sec- Something went wrong"

def get_custom_abuse_response(target_name: str) -> str:
    return f"Chalo {target_name}, time for some reality check! 💅"

def get_random_joke() -> str:
    jokes = [
        "🤣 Aapka pyaar mere computer jaisa hai - memory mein ho ya na ho, butter toh nahi banata!",
        "😂 Pyaar ek game hai aur main expert hoon... chahal karte ho?",
        "🎪 Aapki hasrat bhi computer jaisa hai - hardware sab theek, software naach karti hai!",
        "😄 Love is simple - ek hi chakra chale!"
    ]
    return random.choice(jokes)

def get_random_quote() -> str:
    quotes = [
        "🌟 Zindagi bohot aasan hai, bas isko complex banate ho tum log!",
        "💫 Khud se mohabbat karo, baaki sab theek ho jayega!",
        "✨ Success wo nahi jo sabko dikhe, success wo hai jo aapko mane!",
        "🌈 Every day is a new opportunity to be better!",
        "💖 Aap apne aap ke liye kaafi ho!"
    ]
    return random.choice(quotes)

def get_daily_tip() -> str:
    tips = [
        "💡 Aaj ka tip: Subah jaldi uthne se mood pura din accha rehta hai!",
        "💡 Aaj ka tip: 5 minute meditation aapka stress bahut kam kar dega!",
        "💡 Aaj ka tip: Zyada paani piyo - aapka skin aur health sab theek ho jayega!",
        "💡 Aaj ka tip: Kisi ko thank you kahne se aapka din aur badhiya ho jayega!",
        "💡 Aaj ka tip: Apne aap se pyaar karna seekhte hain tab baaki log bhi pyaar karenge!"
    ]
    return random.choice(tips)

def get_random_compliment() -> str:
    compliments = [
        "Aap so talented ho! 😍",
        "Your smile makes everyone happy~ 💕",
        "Aapka personality amazing hai! 💫",
        "You're actually so inspiring! 🌟",
        "Bilkul unique ho aap! 😊",
        "Your creativity is on another level! 🎨",
        "Aap bahut caring person ho! 💖",
        "You make the world better! 🌍✨"
    ]
    return random.choice(compliments)

def get_random_fortune() -> str:
    fortunes = [
        "🔮 Aapke future mein bahut khushi aa rahi hai!",
        "🔮 Success aapka wait kar rahi hai!",
        "🔮 Aapka luck aaj best hai!",
        "🔮 Something beautiful is coming your way~ 💕",
        "🔮 Aapke sapne bilkul poore hone wale hain!",
        "🔮 Great things are coming soon! 🌟",
        "🔮 Today will bring unexpected joy! 😊"
    ]
    return random.choice(fortunes)

def get_random_dare() -> str:
    dares = [
        "😈 Dare: Apna favorite song gaao!",
        "😈 Dare: Jo bhi first aaya voice message mein bol do!",
        "😈 Dare: Sabko ek compliment do!",
        "😈 Dare: Apna embarrassing story share karo!",
        "😈 Dare: Aaj kisi ko call karke goodmorning bolna!",
        "😈 Dare: Smiling selfie bhejo!",
        "😈 Dare: Dance karo aur ek photo share karo!"
    ]
    return random.choice(dares)

def get_random_truth() -> str:
    truths = [
        "🤔 Truth: Aapka biggest crush kaun hai?",
        "🤔 Truth: Kya secret aapko koi nahi janta?",
        "🤔 Truth: Aapka first love kaisa tha?",
        "🤔 Truth: Aapne kab sab se zyada pyaar feel kiya?",
        "🤔 Truth: Aapka wildest dream kya hai?",
        "🤔 Truth: Aapka biggest fear kya hai?",
        "🤔 Truth: Aapne kabhi jhooth bola kisi se?"
    ]
    return random.choice(truths)

def get_stats():
    return {
        "total_users": len(conversation_history),
        "uptime": "Always ready! 💕"
    }

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

def clear_all_data():
    global conversation_history, group_conversation_history, dirty_conversation_history
    conversation_history = {}
    group_conversation_history = {}
    dirty_conversation_history = {}
    return True

def add_to_group_history(chat_id: str, user_name: str, message: str):
    if chat_id not in group_conversation_history:
        group_conversation_history[chat_id] = []
    group_conversation_history[chat_id].append({
        "role": "user",
        "parts": [{"text": f"{user_name}: {message}"}]
    })
    if len(group_conversation_history[chat_id]) > 50:
        group_conversation_history[chat_id] = group_conversation_history[chat_id][-50:]
