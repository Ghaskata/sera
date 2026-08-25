# Sera Backend — Telegram-First Personal Assistant

Sera is a Telegram-first personal work-and-life assistant. The backend is a FastAPI modular monolith that owns identity, workspaces, connector credentials, ingestion, memory retrieval, and the Telegram interface.

## Week-one product slice

The first production-oriented slice does four things well:

1. Creates a pending Sera account from Telegram.
2. Requires Google sign-in before private workspace data is used.
3. Stores encrypted Google OAuth credentials and indexes read-only Google Drive files.
4. Answers Telegram questions with Gemini using workspace-scoped retrieved context and source citations.

Google sign-in and Google Drive access are implemented together in the first flow. Gmail is available through `/connect_gmail` with a separate read-only consent flow and incremental indexing. Google Calendar is available through `/connect_calendar`, and `/connect_meet` enables read-only Google Meet conference-record and transcript synchronization. Slack and Microsoft Teams now have provider-specific OAuth foundations and read-only sync modules; each still requires its own app registration, redirect URI, and workspace/tenant consent. Google Maps requires a separate API-key-based integration, and Google Keep/Notes remain planned connector modules rather than being silently treated as available through Drive login.

## Prerequisites

- Python 3.12+
- Docker (for Postgres + pgvector)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Google Cloud OAuth client (Web application type) with Drive API enabled; enable Gmail API, Calendar API, and Meet REST API access if those commands are needed
- A Slack app with OAuth v2 redirect URI and read-only conversation-history scopes, if Slack is needed
- A Microsoft Entra app with delegated Microsoft Graph permissions and admin consent where required, if Teams is needed
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
# Fill in TELEGRAM_BOT_TOKEN, Google credentials, Gemini credentials,
# provider OAuth credentials, redirect URIs, and TOKEN_ENCRYPTION_KEY.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
alembic upgrade head
```

Google OAuth requires a public HTTPS callback URI. During local development, run the backend on port 8000, expose it through a tunnel, and register the exact tunnel callback URL in Google Cloud Console and `GOOGLE_OAUTH_REDIRECT_URI`.

## Run

```bash
uvicorn app.main:app --reload
```

The process serves the FastAPI health check and Google, Slack, and Microsoft OAuth callbacks, runs Telegram long polling, and runs the incremental source scheduler. In Telegram, send `/start`, tap the Google sign-in link, approve the requested read-only permissions, and then ask a question. `/login` and `/connect_google` can be used to start the Google flow again; `/connect_drive` remains a compatibility alias. `/connect_gmail`, `/connect_calendar`, and `/connect_meet` request narrower Google provider scopes. `/connect_slack` installs the Slack app, while `/connect_teams` starts Microsoft identity consent. Calendar events are normalized as meetings, Google Meet conference records and available transcript entries are indexed automatically, and Teams calendar meetings are synced with optional transcript retrieval when tenant permissions allow it. `/insights` reports detected repeated work, and `/why <action-key>` explains a candidate’s frequency and time metrics.

## Project layout

```text
app/
  api/routes/               # health and Google OAuth callback
  connectors/catalog.py     # implemented and staged provider capabilities
  connectors/google_drive/  # Google OAuth, Drive sync, extraction
  connectors/google_workspace/ # Gmail, Calendar, and Meet read-only sync
  connectors/slack/          # Slack OAuth v2 and channel-history sync
  connectors/microsoft_teams/ # Microsoft OAuth and Graph meeting sync
  models/                   # users, workspaces, connectors, meetings, documents, chunks, OAuth state
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

The current suite covers chunking, embedding calls, token refresh persistence, RAG workspace isolation/citation behavior, OAuth-state expiry, provider-specific scopes, Google workspace parsing, and work-pattern metrics. The schema migrations for Google identity/OAuth states, work intelligence, and normalized meetings are `1f2c3d4e5f6a_google_identity_oauth_state.py`, `2a3b4c5d6e7f_work_intelligence.py`, and `3b4c5d6e7f8a_meetings.py`.
