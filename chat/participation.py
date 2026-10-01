import random


def should_participate(context, direct_mention: bool = False, reply_to_bot: bool = False, question: bool = False, image: bool = False, probability: float = 0.15) -> bool:
    if direct_mention or reply_to_bot or question or image:
        return True
    return random.random() < min(1.0, max(0.0, probability))
