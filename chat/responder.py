import random

from chat.modes import ChatMode


def get_mode_style(mode: str) -> str:
    if mode == ChatMode.LOVE:
        return "warm and affectionate"
    if mode == ChatMode.ABUSE:
        return "playful and roasted"
    return "natural and balanced"


def build_reply_for_mode(user_message: str, mode: str) -> str:
    text = (user_message or "").strip()
    if not text:
        return "hmm?"
    lowered = text.lower()
    if mode == ChatMode.LOVE:
        if "hi" in lowered or "hello" in lowered:
            return "heyy, I’m glad you messaged me ❤️"
        return "aww, that’s sweet 😭❤️"
    if mode == ChatMode.ABUSE:
        if "no" in lowered:
            return "bro, the confidence is strong but the facts are weak 😭"
        return "okay okay, look who suddenly became a comedian 😌"
    if "what" in lowered and "?" in text:
        return "give me a sec, I’ll answer that properly."
    return random.choice(["heyy 😂", "wait what happened", "ohhh I get you", "that’s actually kinda funny", "nahhh 💀"])
