from character.profile import build_character_prompt


def default_prompt(mode: str = 'normal') -> str:
    return build_character_prompt(mode)
