# Sera MVP — Backend + Telegram Bot (Google Drive RAG) — Design

**Date:** 2026-08-06
**Status:** Approved

## Context

Sera is a multi-year, multi-phase "AI Operating System for Work" (see `system design/PRD.md`). Building the full product at once is out of scope. This spec covers the **first buildable slice**:

- A shared backend that will eventually serve web, mobile app, and Telegram — but is built first, and shipped first, through a **Telegram bot** interface (web frontend is being built separately and is out of scope here).
- A single connector (**Google Drive**) feeding a RAG (retrieval-augmented generation) pipeline.
- Multi-user from day one (each Telegram user gets their own account, workspace, and Google Drive connection).

Goal: a user can `/start` the bot, connect their Google Drive, ask a question in Telegram, and get back an answer with citations pointing at the source file(s).

## Decisions (locked in during brainstorming)

- **First slice:** single connector (Google Drive) + RAG Q&A — not the Daily Briefing/autonomous-agent feature, not multi-connector.
- **Architecture:** modular monolith (Approach A). One FastAPI codebase with an internal service layer (`auth`, `workspaces`, `connectors/google_drive`, `ingestion`, `search`). The Telegram bot process imports and calls this service layer directly (in-process, no HTTP hop). The same service layer is exposed over REST so future web/app clients can call it without duplicating logic.
- **LLM:** Google Gemini (free tier) for answer generation.
- **Embeddings:** Ollama, local, `nomic-embed-text` model — free, no API cost.
- **Database:** PostgreSQL + pgvector, run locally via Docker for now (no managed cloud DB yet).
- **Background jobs:** in-process scheduler (APScheduler) for periodic Drive sync — no Celery/Redis yet; add only when justified by load.
- **Users:** multi-user from day one — each Telegram user maps to their own `users` row, own `workspace`, own `connectors` row (own OAuth tokens).

## Data Model

```
users
  id, telegram_user_id UNIQUE, name, created_at

workspaces
  id, owner_id → users.id, name, created_at

connectors
  id, workspace_id → workspaces.id, provider ('google_drive'),
  oauth_tokens (encrypted at rest), status, last_sync_at

documents
  id, workspace_id → workspaces.id, connector_id → connectors.id,
  external_id (Drive file id), title, mime_type, updated_at

chunks
  id, document_id → documents.id, text, embedding vector(768),
  metadata jsonb (e.g. { "page": 3, "drive_link": "..." })

queries_log
  id, workspace_id → workspaces.id, question, answer,
  sources jsonb, created_at
```

One Telegram user = one `users` row = one default `workspace` for now. The PRD's multi-workspace-per-user model is deferred; the schema should not preclude adding it later (workspace_id is already the scoping key everywhere).

## Onboarding & OAuth Flow

1. `/start` in Telegram → create (or fetch) `users` row keyed by `telegram_user_id`, create a default `workspace` if none exists.
2. `/connect_drive` → bot sends the user a Google OAuth consent URL.
3. User completes consent in their browser → Google redirects to a FastAPI callback endpoint (`GET /oauth/google/callback`) → backend exchanges the code for tokens, stores them (encrypted) on the `connectors` row, and confirms back to the user (via a "connected, return to Telegram" message/deep link).
4. Immediately after connecting, trigger an initial full sync (see Ingestion Pipeline).

**Local-dev constraint:** Google OAuth requires a public HTTPS redirect URI. During development this repo will use an **ngrok (or cloudflared) tunnel** pointed at the local FastAPI server. Production deployment will use a real domain. This is a dev-environment detail, not a design fork — the callback endpoint code is identical either way.

## Ingestion Pipeline (Google Drive connector)

```
Drive API (list on first sync / changes.list on incremental sync)
  → download file content
  → extract text (PDF, Google Docs, Google Sheets — plain text/OCR-less only for MVP)
  → chunk (~500 tokens, with overlap)
  → embed each chunk (Ollama, nomic-embed-text)
  → upsert into `chunks` (pgvector column) + `documents`
```

- **Full sync**: runs once, right after a connector is first connected.
- **Incremental sync**: APScheduler job per workspace connector, every N minutes (e.g. 15), using Drive's `changes.list` API so only new/modified files are re-processed — not a full re-embed.
- Files with no extractable text (e.g. scanned images without OCR) are skipped and logged; OCR is explicitly out of scope for this slice.

## Query Flow (RAG)

```
Telegram message (question)
  → embed question (Ollama)
  → pgvector cosine similarity search, top-k chunks, scoped to that workspace_id
  → Gemini generates an answer using the retrieved chunks as context
  → reply in Telegram: answer + source list (file name + Drive link)
  → log to queries_log
```

If no chunk clears a minimum similarity threshold, the bot says it couldn't find relevant information rather than letting Gemini answer ungrounded — citations are a hard requirement carried over from the PRD (Section 3), not optional polish.

## Error Handling

- **OAuth token expiry**: auto-refresh using the stored refresh_token; if refresh itself fails, mark the connector `status = 'needs_reauth'` and prompt the user to `/connect_drive` again.
- **Drive API rate limits / 5xx**: retry with exponential backoff; permanent failures are logged per-file and skipped, not fatal to the whole sync run.
- **Telegram 4096-character message limit**: long answers are split into multiple sequential messages.
- **Unsupported/unreadable files**: skipped and logged, sync continues.

## Testing

- **Unit tests**: chunking logic (boundary/overlap correctness), embedding service (Ollama call mocked), OAuth token refresh logic.
- **Integration test**: seed the test DB with known chunks for a fake workspace, ask a question whose answer is only in one specific chunk, assert that chunk is retrieved and cited (Gemini call mocked to return a canned response referencing the injected context).

## Explicitly Out of Scope for This Slice

- Web/app frontend (built separately, elsewhere).
- Any connector other than Google Drive (Slack, Gmail, Notion, ChatGPT/Claude/Gemini history, Google Notes, etc. — PRD Phase 2+).
- Daily Briefing / autonomous agent runs (PRD Section 8.8).
- Multi-workspace-per-user, roles/permissions, team collaboration (PRD Phase 3).
- OCR for scanned documents.
- Celery/Redis background job infrastructure (revisit if APScheduler + in-process jobs become insufficient).
