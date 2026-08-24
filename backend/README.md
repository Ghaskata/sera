# Sera Backend — Telegram RAG MVP

FastAPI modular monolith backend for Sera's first buildable slice: a Telegram
bot that answers questions using each user's Google Drive files (RAG). See
`../docs/superpowers/specs/2026-08-06-telegram-rag-mvp-design.md` for the
full design.

## Prerequisites

- Python 3.12
- Docker (for Postgres + pgvector)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Google Cloud OAuth client (Web application type) with the Drive API
  enabled, and a **Gemini API key**
- For local OAuth testing: an ngrok/cloudflared tunnel, since Google OAuth
  requires a public HTTPS redirect URI

## Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

# start Postgres+pgvector
docker compose up -d

cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN, GOOGLE_CLIENT_ID/SECRET, GEMINI_API_KEY,
# GOOGLE_OAUTH_REDIRECT_URI (your tunnel URL), and generate a
# TOKEN_ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

This single process serves the FastAPI app (health check + the Google OAuth
callback) **and** runs the Telegram bot via long polling, so the OAuth
callback can notify the right Telegram user when a Drive connection finishes
syncing.

In Telegram: `/start`, then `/connect_drive`, complete the Google consent
screen, then just ask a question.

## Project layout

```
app/
  models/           # SQLAlchemy models — users, workspaces, connectors, documents, chunks, queries_log
  services/         # accounts, connectors, chunking, embeddings (Gemini), llm (Gemini)
  connectors/google_drive/   # OAuth, sync (full + incremental via changes.list), text extraction
  search/rag.py     # embed question → pgvector similarity search → Gemini answer → citations
  telegram_bot/     # bot wiring + command/message handlers
  api/routes/       # health check, Google OAuth callback
  scheduler.py      # APScheduler job: incremental Drive sync every N minutes
  main.py           # FastAPI app + lifespan (starts bot polling + scheduler)
```

## Notes

- Every DB row scoped by `workspace_id`; the Telegram RAG flow currently
  maps 1 Telegram user → 1 default workspace, but nothing in the schema
  assumes that stays true.
- Answers are grounded only in retrieved chunks above `RAG_MIN_SIMILARITY`;
  if nothing clears the bar, the bot says so instead of letting Gemini
  answer ungrounded.
- Out of scope for this slice (see design doc): any connector besides
  Google Drive, Daily Briefing/autonomous runs, multi-workspace-per-user,
  OCR, Celery/Redis.
