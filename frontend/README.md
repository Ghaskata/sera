# SERA Dashboard

A Vite + React + TypeScript starter for the SERA workspace dashboard. It includes Google session login, authenticated connector cards, connection states, work-detective patterns, and a Memory Search surface for the Gemini RAG endpoint.

## Run locally

```bash
pnpm install
pnpm dev
```

Open `http://localhost:5173`. The Vite proxy forwards `/auth`, `/connectors`, `/rag`, and `/oauth` to the FastAPI service at `http://127.0.0.1:8000`.

The first screen calls `GET /auth/me`. If no secure `HttpOnly` SERA session cookie exists, it displays **Continue with Google**, which starts `GET /auth/google/start`. After Google redirects through `/auth/google/callback`, FastAPI sets the session cookie and redirects back to the dashboard.

Authenticated dashboard calls use server-side routes only:

| Dashboard action | Route |
|---|---|
| Current user/workspace | `GET /auth/me` |
| Connected source status | `GET /auth/connectors` |
| Start provider setup | `GET /auth/connectors/{provider}/start` |
| Workspace-scoped RAG | `POST /auth/rag/query` |
| Logout and revoke session | `POST /auth/logout` |

The browser never receives `RAG_QUERY_TOKEN`, Google/Slack/Microsoft client secrets, or provider access tokens. The backend derives `workspace_id` from the opaque, database-backed session cookie. Connector cards redirect through the backend setup route so OAuth state is generated and consumed server-side.

## Production build

```bash
pnpm build
pnpm preview
```

For staging/production, serve the dashboard and API behind HTTPS and set `WEB_COOKIE_SECURE=true`. Register both Google callbacks in Google Cloud Console:

```text
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/oauth/google/callback
GOOGLE_WEB_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Replace the localhost values with the public HTTPS callback URLs in the deployment environment. The current dashboard intentionally leaves advanced settings and live work-detective counters as follow-up slices; the secure login, connector status, setup redirects, and RAG proxy are wired.
