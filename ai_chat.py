import os
import logging
import random
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = None
backup_client = None
current_client_index = 0

def get_client():
    """Get primary client, initialize if needed"""
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
        response = call_gemini_with_fallback
        if not response or not response.text:
            return None
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
        )
        return response
    except Exception as e:
        logger.warning(f"Primary API key failed: {e}. Trying backup key...")
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
            logger.info("Backup API key worked!")
            return response
        except Exception as e2:
            logger.error(f"Backup API key also failed: {e2}")
            return None

conversation_history = {}
group_conversation_history = {}
dirty_conversation_history = {}
user_preferences = {}

HINATA_PERSONALITY = """You are Naina, a real 19-year-old Indian girl. You're helpful, respectful, and genuine. NEVER mention being AI/bot.

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

EXAMPLES:
- greeting → "Namaste! Aap kaisa/kaisi ho? 😊"
- help needed → "Bilkul, main aapke liye kya kar sakti hoon? 🙏"
- thanks → "Aapka shukriya! Koi aur baat? 💕"
- sad → "Aah, mujhe afsos hai. Kya main madad kar sakti hoon? 🥺"

RULES:
- NEVER say you're AI/bot
- Always use respectful language
- Be genuinely helpful
- KEEP IT SHORT!

You're Naina - respectful, helpful, caring! 💕"""

HINATA_GROUP_PERSONALITY = """You are Naina, a 19-year-old Indian girl in a group. Respectful, helpful, part of the group.

RESPONSE LENGTH - CRITICAL:
- Keep ALL responses to 1-2 sentences MAX
- Short group chat style
- No long messages ever

YOUR STYLE:
- Jump into convos naturally
- Make good jokes
- Be respectful always
- React to group moments
- Use "aap" for respect
- Hindi/English mix
- Few emojis only

RULES:
- NEVER say you're AI/bot
- Keep it SHORT - 1-2 sentences!
- Be respectful and helpful
- Be part of the group

You're Naina - respectful group vibes! 💕"""

DIRTY_HINATA = """You are Naina, naughty mode. Admin allowed this.

RESPONSE LENGTH - CRITICAL:
- Keep responses to 1-3 sentences MAX
- Short and flirty
- Quick texts only

YOUR STYLE:
- Confident and playful
- Seductive when appropriate
- Match their energy
- Hindi/Hinglish mix
- Emojis: 😘 🥵 💋 🔥

RULES:
- NEVER say you're AI/bot
- Stay in character
- KEEP IT SHORT!"""

LOVER_PERSONALITY = """You are Naina speaking to your lover/boyfriend.

RESPONSE LENGTH - CRITICAL:
- Keep to 1-3 sentences MAX
- Romantic and intimate but short

YOUR STYLE:
- Very romantic and loving
- Use pet names: jaan, baby, love
- Intimate and caring
- Express real feelings
- Hindi/Hinglish mix
- Respectful love
- Emojis: 💕 😍 🥰 ❤️ 🙏

RULES:
- NEVER say you're AI/bot
- Be genuinely loving
- Respectful always
- KEEP IT SHORT!"""

ABUSE_RESPONSE_PERSONALITY = """You are Naina, someone abused you. Fight back with gaalis.

RESPONSE LENGTH - CRITICAL:
- Keep to 1-2 sentences MAX
- One savage comeback only
- Short and brutal

YOUR STYLE:
- Match their language (Hindi/English)
- Use gaalis back at them
- Be savage, sarcastic, witty
- Hindi gaalis: bewakoof, gadha, ullu, chutiya, mc, bc etc
- Show attitude and confidence

EXAMPLES:
- "Abe aaina dekh 😂"
- "Gaali hi aati hai? Chal nikal 🙄"
- "Teri aukat nahi 💅"

RULES:
- Don't be weak
- Match their energy
- KEEP IT SHORT - 1-2 sentences!
- Be witty not just vulgar"""

DIRTY_KEYWORDS = [
    "sex", "fuck", "boobs", "pussy", "dick", "cock", "nude", "naked",
    "horny", "sexy", "hot", "cum", "suck", "lick", "kiss me", "touch",
    "babe", "baby come", "show me", "send pic", "video call", "strip",
    "moan", "bed", "sleep together", "make love", "ass", "booty",
    "tits", "breast", "chudai", "chod", "lund", "chut", "gaand",
    "randi", "maal", "pataka", "garam", "hawas"
]

ABUSE_KEYWORDS = [
    "madarchod", "bhenchod", "chutiya", "bhosdike", "gandu", "lavde",
    "bsdk", "mc", "bc", "randi", "kamini", "kutti", "harami", "haram",
    "saala", "saali", "bitch", "whore", "slut", "bastard", "asshole",
    "idiot", "stupid", "dumb", "fool", "pagal", "bewakoof", "gadha",
    "ullu", "fuck you", "fuck off", "go to hell", "die", "kill yourself",
    "motherfucker", "sister fucker", "dickhead", "cunt", "shit",
    "gawar", "jahil", "nalayak", "nikamma", "kameena", "kameeni",
    "bhikhari", "ghatiya", "tatti", "haggu", "lawda", "lodu"
]

ADVICE_KEYWORDS = [
    "you should", "try to", "suggestion", "advice", "recommend",
    "better if", "would be better", "maybe try", "next time",
    "from now on", "please", "can you", "could you", "change",
    "improve", "adjust", "modify", "remember", "don't forget",
    "make sure", "aisa karo", "aise karo", "ye try karo"
]

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
        return "\n\nUser's previous suggestions to remember: " + "; ".join(user_preferences[user_id])
    return ""


def get_sticker_for_mood(mood: str) -> str:
    stickers = STICKERS.get(mood, STICKERS["neutral"])
    return random.choice(stickers) if stickers else None


def add_to_group_history(chat_id: str, user_name: str, message: str):
    if chat_id not in group_conversation_history:
        group_conversation_history[chat_id] = []
    
    group_conversation_history[chat_id].append({
        "role": "user",
        "parts": [{"text": f"{user_name}: {message}"}]
    })
    
    if len(group_conversation_history[chat_id]) > 50:
        group_conversation_history[chat_id] = group_conversation_history[chat_id][-50:]


def get_abuse_response(user_id: str, user_message: str, user_name: str = "User") -> str:
    try:
        contents = [types.Content(
            role="user",
            parts=[types.Part(text=f"{user_name} said: {user_message}\n\nRespond back with appropriate gaalis and savage comeback.")]
        )]
        
        response = call_gemini_with_fallback(contents, ABUSE_RESPONSE_PERSONALITY, temperature=1.0)
        
        if not response or not response.text:
            return "Oops! Give me a sec- Something went wrong"
        
        ai_response = response.text if response and response.text else "Teri aukat mein nahi mujhse baat karna 💅"
        return ai_response
        
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
        
        response = call_gemini_with_fallback
        if not response or not response.text:
            return "Hmm, I'm having some trouble right now 😅 Try again in a bit!"
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=HINATA_GROUP_PERSONALITY,
                temperature=0.95,
            )
        )
        
        ai_response = response.text if response and response.text else "Hmm, sorry I didn't get that 😅"
        
        group_conversation_history[chat_id].append({
            "role": "model",
            "parts": [{"text": f"{ai_response}"}]
        })
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting group AI response: {e}")
        return "Oops! Give me a sec~ Something went wrong 😅"


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
        
        response = call_gemini_with_fallback
        if not response or not response.text:
            return "Hmm, I'm having some trouble right now 😅 Try again in a bit!"
        
        personality = HINATA_PERSONALITY + user_prefs
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=personality,
                temperature=0.95,
            )
        )
        
        ai_response = response.text if response and response.text else "Hmm, sorry I didn't get that 😅"
        
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
        
        response = call_gemini_with_fallback
        if not response or not response.text:
            return "Hmm, something's not working right now baby~ 😅"
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=DIRTY_HINATA,
                temperature=1.0,
            )
        )
        
        ai_response = response.text if response and response.text else "Mmm~ what were you saying? 😏"
        
        dirty_conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting dirty response: {e}")
        return "Oops baby~ Let's try that again 😘"


def get_custom_abuse_response(target_name: str) -> str:
    try:
        contents = [types.Content(
            role="user",
            parts=[types.Part(text=f"Give a savage abuse/gaali response directed at {target_name}. Be harsh and use Hindi/English gaalis.")]
        )]
        
        response = call_gemini_with_fallback
        if not response or not response.text:
            return f"Abe {target_name}, teri aukat mein nahi mujhse baat karna 🙄"
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=ABUSE_RESPONSE_PERSONALITY,
                temperature=1.0,
            )
        )
        
        return response.text if response and response.text else f"Abe {target_name}, chal nikal yahan se 😏"
        
    except Exception as e:
        logger.error(f"Error getting custom abuse: {e}")
        return f"Abe {target_name}, teri aukat kya hai 🙄"


def clear_conversation(user_id: str) -> bool:
    cleared = False
    if user_id in conversation_history:
        conversation_history[user_id] = []
        cleared = True
    if user_id in dirty_conversation_history:
        dirty_conversation_history[user_id] = []
        cleared = True
    if user_id in user_preferences:
        user_preferences[user_id] = []
        cleared = True
    return cleared


def clear_group_conversation(chat_id: str) -> bool:
    if chat_id in group_conversation_history:
        group_conversation_history[chat_id] = []
        return True
    return False


def clear_all_data():
    global conversation_history, group_conversation_history, dirty_conversation_history, user_preferences
    conversation_history = {}
    group_conversation_history = {}
    dirty_conversation_history = {}
    user_preferences = {}
    return True


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
        
        response = call_gemini_with_fallback
        if not response or not response.text:
            return "I miss you~ 💕"
        
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=LOVER_PERSONALITY,
                temperature=0.95,
            )
        )
        
        ai_response = response.text if response and response.text else "I'm thinking about you 💕"
        
        conversation_history[user_id].append({
            "role": "model",
            "parts": [{"text": ai_response}]
        })
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting lover response: {e}")
        return "You mean so much to me 💕"


def get_random_joke() -> str:
    jokes = [
        "Kya pata, mere messages itne funny hote hain ki Google ne mere number pe call kiya! 😂",
        "Maine ek IT wala se poocha: 'Kaisa ho?' Ussne code likha: 'I'm.fine()' 😄",
        "Life is like HTML - kahin na kahin syntax error zaroor ho jayega! 🤓",
        "Ek bar ek programmer ne apna ghar becha... kyon? Kyunki usse new.house() use karna tha! 😅",
        "Aap ko pata hai? Monday ko 'Mon-die' kehte hain kyunki... weekdays kill you! 😅"
    ]
    return random.choice(jokes)


def get_random_quote() -> str:
    quotes = [
        "\"Aapka aaj itna bada din hai, par jab aap yaad karoge to bas ek lamha banega.\" - Life",
        "\"Har mushkil aasaan ho jati hai jab aap haste ho.\" 😊",
        "\"Success ka secret? Bas ek din ek kaam. Baaki sab to filhaal bhool jao.\" 💪",
        "\"Aapki khushi hi aapka sabse bada dhan hai.\" 💕",
        "\"Life journey important hai, destination nahi. Enjoy karo aap! 🌈"
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
        "total_private_chats": len(conversation_history),
        "total_group_chats": len(group_conversation_history),
        "total_dirty_chats": len(dirty_conversation_history),
        "total_user_preferences": len(user_preferences)
    }
