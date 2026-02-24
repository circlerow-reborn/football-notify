## Football News → Telegram (Vietnamese Translation)

Tracks football news from RSS feeds, translates to Vietnamese using Gemini, and posts updates to Telegram. Sent articles are deduplicated via MongoDB.

### Requirements

- Python 3.10+
- MongoDB (local or Atlas)

### Setup

1. Install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:

```bash
cp .env.example .env
```

Fill in:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GEMINI_API_KEY`
- `MONGODB_URI`

3. Run:

```bash
python main.py
```

### Notes

- **Chat ID**: for a private chat, message the bot then use Telegram `getUpdates` to find `chat.id`. For a channel/supergroup, you’ll usually see IDs like `-100...`.
- **MongoDB**: the app creates a unique index on `article_id` to avoid duplicates.
- **RSS feeds**: edit `RSS_FEEDS` (comma-separated) in `.env`.
