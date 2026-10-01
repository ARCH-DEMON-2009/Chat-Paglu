from character.profile import load_character_profile


def get_personality_summary() -> str:
    profile = load_character_profile()
    personality = profile.get("personality", [])
    return ", ".join(personality) if personality else "friendly and playful"
