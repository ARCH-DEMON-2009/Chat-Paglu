import random


def should_participate(context, bot_last_action_at: float | None = None, direct_mention: bool = False, reply_to_bot: bool = False, question: bool = False, image: bool = False) -> bool:
    if direct_mention or reply_to_bot or question or image:
        return True
    if bot_last_action_at is not None:
        if (random.random() * 100) < 25:
            return True
    return random.random() < 0.15
