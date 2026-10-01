import asyncio
import random
from typing import Tuple


def get_typing_delay(length: int, minimum: float = 0.5, maximum: float = 2.0) -> float:
    normalized = min(max(length / 60.0, 0.0), 1.0)
    return min(max(minimum + normalized * (maximum - minimum), minimum), maximum)


async def send_typing(context, chat_id: int, delay_seconds: float | None = None):
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    if delay_seconds is not None:
        await asyncio.sleep(delay_seconds)
