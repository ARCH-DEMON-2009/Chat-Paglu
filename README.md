# Chat-Paglu

Chat-Paglu is a Telegram group chat assistant with a fictional AI-girl personality, group awareness, memory, typing indicators, and optional image-question analysis.

## Installation

1. Clone the repo.
2. Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your Telegram token and Gemini API key.

## Environment variables

Copy `.env.example` to `.env` and fill in the values.

Required values:

- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY` (optional; without it the bot uses offline fallback replies)
- `ADMIN_IDS` (Telegram user IDs allowed to use admin commands)

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
- `/lover @username` - send a one-shot affectionate message in a group
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

## Database

SQLite is the default. To use Supabase Postgres, run `supabase_schema.sql` in the Supabase SQL editor, set `USE_SUPABASE=true`, and set `DATABASE_URL` to the project's PostgreSQL connection URL. URL-encode reserved characters in the database password. Postgres connections require SSL.

The bot stores user preferences and facts in the configured database. Memory is intentionally limited to useful, non-sensitive facts, and admins can clear a user's memory with `/clear_memory [user_id]`.

## Image and question handling

When a user uploads an image, the app checks for a question or simple readable text and answers it if possible. It avoids hallucinating when the image is unclear.

## Deployment

This project is compatible with Render and Procfile-based deployment. The service uses a Python worker process.

For group replies beyond commands, mentions, and questions, disable BotFather's group privacy mode or grant the bot suitable group permissions so Telegram delivers ordinary group messages.
