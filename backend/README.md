# Sera Backend — Telegram-First Personal Assistant

Sera is a Telegram-first personal work-and-life assistant. The backend is a FastAPI modular monolith that owns identity, workspaces, connector credentials, ingestion, memory retrieval, and the Telegram interface.

## Week-one product slice

The first production-oriented slice does four things well:

1. Creates a pending Sera account from Telegram.
2. Requires Google sign-in before private workspace data is used.
3. Stores encrypted Google OAuth credentials and indexes read-only Google Drive files.
4. Answers Telegram questions with Gemini using workspace-scoped retrieved context and source citations.

Google sign-in and Google Drive access are implemented together in the first flow. Gmail is available through `/connect_gmail` with a separate read-only consent flow and incremental indexing. Google Calendar is also available through `/connect_calendar`; Slack and Microsoft Teams require their own provider-specific OAuth flows. Google Maps requires a separate API-key-based integration, and Google Keep/Notes and Meet transcripts are planned connector modules rather than being silently treated as available through Drive login.

## Prerequisites

- Python 3.12+
- Docker (for Postgres + pgvector)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Google Cloud OAuth client (Web application type) with the Drive API enabled; enable Gmail API and Calendar API if those commands are needed
- A Gemini API key
- For local OAuth testing: an ngrok or cloudflared HTTPS tunnel

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

docker compose up -d db
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN, GOOGLE_CLIENT_ID/SECRET,
# GEMINI_API_KEY, GOOGLE_OAUTH_REDIRECT_URI, and TOKEN_ENCRYPTION_KEY.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
alembic upgrade head
```

Google OAuth requires a public HTTPS callback URI. During local development, run the backend on port 8000, expose it through a tunnel, and register the exact tunnel callback URL in Google Cloud Console and `GOOGLE_OAUTH_REDIRECT_URI`.

## Run

```bash
uvicorn app.main:app --reload
```

The process serves the FastAPI health check and Google OAuth callback, runs Telegram long polling, and runs the incremental Google-source sync scheduler. In Telegram, send `/start`, tap the Google sign-in link, approve the requested read-only permissions, and then ask a question. `/login` and `/connect_google` can be used to start the flow again; `/connect_drive` remains as a compatibility alias. After the initial connection, `/connect_gmail` and `/connect_calendar` request their narrower provider-specific scopes. `/insights` reports detected repeated work, and `/why <action-key>` explains a candidate’s frequency and time metrics.

## Project layout

```text
app/
  api/routes/               # health and Google OAuth callback
  connectors/catalog.py     # implemented and staged provider capabilities
  connectors/google_drive/  # Google OAuth, Drive sync, extraction
  connectors/google_workspace/ # Gmail and Calendar read-only sync
  models/                   # users, workspaces, connectors, documents, chunks, OAuth state
  services/                 # account linking, encrypted tokens, chunking, embeddings, Gemini
  search/rag.py             # workspace-scoped retrieval and cited answers
  telegram_bot/             # onboarding, Google sign-in, and question handlers
  scheduler.py              # periodic incremental Google-source sync
alembic/versions/           # schema migrations
```

## Security model

OAuth state is a cryptographically random, short-lived, one-time value stored server-side and tied to the initiating Telegram user. Google profile identity is fetched from Google’s OpenID userinfo endpoint after token exchange. OAuth tokens are encrypted at rest. Every retrieval is scoped by the user’s workspace. No external write action is implemented or executed in this slice.

## Verification

```bash
pytest -q
```

The current suite covers chunking, embedding calls, token refresh persistence, RAG workspace isolation/citation behavior, OAuth-state expiry, provider-specific Google scopes, and work-pattern metrics. The schema migrations for Google identity/OAuth states and work intelligence are `1f2c3d4e5f6a_google_identity_oauth_state.py` and `2a3b4c5d6e7f_work_intelligence.py`.
