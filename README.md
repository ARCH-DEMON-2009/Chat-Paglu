# Chat-Paglu

Chat-Paglu is a Telegram group chat assistant with a fictional AI-girl personality, group awareness, memory, typing indicators, and optional image-question analysis.

## Installation

1. Clone the repo.
2. Create a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` and fill in the values.

Required values:

- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`
- `ADMIN_IDS`

Optional values:

- `GEMINI_API_KEY_BACKUP`
- `AI_PROVIDER`
- `AI_MODEL`
- `VISION_MODEL`
- `DATABASE_URL`
- `GROUP_RESPONSE_PROBABILITY`
- `TYPING_DELAY_MIN`
- `TYPING_DELAY_MAX`
- `MEMORY_ENABLED`
- `VISION_ENABLED`
- `GROUP_PARTICIPATION_ENABLED`
- `LOVE_MODE_ALLOWED_IN_GROUPS`

## Running the bot

```bash
python main.py
```

## Commands

- `/help`
- `/love`
- `/abuse`
- `/stats`
- `/reload`
- `/setname`
- `/setprompt`
- `/memory`
- `/clear_memory`
- `/participation`
- `/cooldown`
- `/vision`
- `/admin`

## Memory system

The bot stores user preferences and facts in SQLite. Memory is intentionally limited to useful, non-sensitive facts, and users can request memory removal via admin tools.

## Image and question handling

When a user uploads an image, the app checks for a question or simple readable text and answers it if possible. It avoids hallucinating when the image is unclear.

## Deployment

This project is compatible with Render and Procfile-based deployment. The service uses a Python worker process.
