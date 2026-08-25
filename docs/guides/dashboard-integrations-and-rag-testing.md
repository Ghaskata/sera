# SERA Dashboard Integrations and Gemini RAG Testing Guide

This guide explains how to add a web dashboard for SERA’s connector catalog, connection states, setup actions, Google Maps/Notes, social connector foundations, and Gemini RAG queries. The current repository contains the FastAPI backend and Telegram interface; it does not yet contain a web frontend. The examples below are therefore intended for a future React or Next.js dashboard that consumes the existing backend contracts.

## 1. Dashboard information architecture

Use three primary surfaces rather than one large settings page. The **Connected Accounts** surface answers “what is connected and when did it last sync?”, the **Connectors Catalog** surface answers “what can SERA connect to?”, and the **Memory Search** surface answers “what does SERA remember about my work?”. Keep setup and search separate so OAuth consent is never confused with a normal AI query.

| Dashboard component | Purpose | Backend contract |
|---|---|---|
| `ConnectionGrid` | Show provider cards, status, last sync, and next action. | `GET /connectors/catalog` plus an authenticated workspace-status endpoint when the web session is added. |
| `ConnectorCard` | Render one provider’s identity, capabilities, setup mode, and warnings. | Catalog fields: `provider`, `display_name`, `auth_family`, `capabilities`, `status`, `setup_mode`, `note`. |
| `SetupButton` | Start provider-specific consent or configuration. | OAuth redirect for Google/Slack/Teams; API-key admin form for Maps; admin-gated setup for Keep. |
| `SyncStatus` | Show `connected`, `pending`, `needs_reauth`, `never synced`, or the last sync timestamp. | Connector status record from the authenticated backend. |
| `MemorySearch` | Query all permitted connected sources and display citations. | `POST /rag/query` for local/admin testing; replace the test-token boundary with user-session auth before public release. |
| `SourceChips` | Make answer provenance visible and filterable. | RAG response `sources[]`: `title`, `source`, `date`, `person`, `url`, `drive_link`. |

## 2. Provider card data model

Fetch the catalog once on dashboard load and map each record to a card. Do not hard-code provider capability text in the frontend because the catalog deliberately distinguishes fully implemented connectors from catalog-only foundations.

```ts
export type ConnectorDefinition = {
  provider: string;
  display_name: string;
  auth_family: string;
  capabilities: string[];
  status: string;
  setup_mode: "oauth" | "api_key" | "bot_token";
  note: string;
};

export async function loadConnectorCatalog(): Promise<ConnectorDefinition[]> {
  // Use /api/connectors/catalog only if the frontend proxy adds the /api prefix.
  const response = await fetch("/connectors/catalog", {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Could not load connector catalog");
  return response.json();
}
```

For the first frontend slice, group cards into **Work & Google**, **Communication**, **Meetings**, **Maps & Notes**, and **Social**. Use the backend `status` to drive the call-to-action. `implemented` cards can show **Connect** or **Reconnect**. `implemented_foundation` cards should show **Configure** plus the provider limitation. `catalog_foundation` cards should show **Coming after provider setup** rather than pretending that OAuth is already available.

```tsx
function ConnectorCard({ item, connected, onSetup }: Props) {
  const foundation = item.status.endsWith("foundation");
  const action = foundation ? "Configure" : connected ? "Reconnect" : "Connect";

  return (
    <article className="rounded-xl border bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold">{item.display_name}</h3>
          <p className="mt-1 text-sm text-slate-600">{item.note}</p>
        </div>
        <StatusBadge status={connected ? "connected" : item.status} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {item.capabilities.map((capability) => (
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs" key={capability}>
            {capability}
          </span>
        ))}
      </div>
      <button
        className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        onClick={() => onSetup(item)}
        disabled={item.status === "catalog_foundation"}
      >
        {item.status === "catalog_foundation" ? "Provider setup required" : action}
      </button>
    </article>
  );
}
```

## 3. Setup actions by provider

Keep setup actions provider-specific. Google Drive, Gmail, Calendar, Meet, and Notes use Google OAuth with different scopes. Slack and Teams use their own OAuth applications. Google Maps uses a restricted server-side API key and must not be presented as a user-account OAuth connection. Social catalog entries require individual provider implementation and approval before their buttons become active.

| Provider group | Frontend action | Expected result |
|---|---|---|
| Google Drive/Gmail/Calendar/Meet/Notes | Navigate to a backend-generated OAuth URL. | Consent page, callback, connector creation, and first sync. |
| Slack | Show **Continue setup in Slack** and navigate to the Slack OAuth URL. | Slack workspace installation and read-only history sync. |
| Teams | Show **Continue setup in Teams** and navigate to Microsoft consent. | Delegated Graph consent and meeting sync if tenant policy allows. |
| Google Maps | Open an admin configuration form or show configured/not configured state. | Backend receives `GOOGLE_MAPS_API_KEY`; no user OAuth account is created. |
| Discord/LinkedIn/Reddit/X/Facebook | Show disabled foundation state and provider requirements. | No false connection; activate only after a real OAuth/sync module exists. |

Always show a consent explanation before redirecting. For example: “SERA will read only the selected source, index it into your private workspace, and show citations in answers. No messages or calendar events will be changed.”

## 4. Connected-account status UI

The current Telegram interface exposes `/status` and `/connections`. For the web dashboard, add an authenticated endpoint that resolves the current user from the web session and returns connector rows for that workspace. Do not copy the local/admin `workspace_id` plus `X-RAG-Token` testing pattern into a public browser endpoint. The browser should use the application’s normal session or a short-lived server-issued token.

Recommended response shape:

```json
{
  "workspace_id": "workspace-uuid",
  "connectors": [
    {
      "provider": "google_gmail",
      "display_name": "Gmail",
      "status": "connected",
      "last_sync_at": "2026-08-25T08:40:00Z",
      "capabilities": ["read", "search", "index"]
    }
  ]
}
```

Render a clear sync status instead of a binary connected flag. Use **Connected**, **Syncing**, **Needs re-authentication**, **Never synced**, and **Not connected**. A failed Slack private-channel permission should appear as a connector-level warning and should not hide Gmail or Drive status.

## 5. Memory Search component

The current backend exposes a deliberately protected testing endpoint at `POST /rag/query`. It uses the Gemini-backed multi-source RAG pipeline, retrieves chunks by workspace, optionally filters by exact source labels, returns citations, and logs the query. The source labels used by ingestion include values such as `Google Drive`, `Gmail`, `Google Calendar`, `Google Meet`, `Google Keep`, `Slack`, and `Microsoft Teams`.

```ts
type RagQuery = {
  workspace_id: string;
  question: string;
  source_types?: string[];
};

type RagResponse = {
  answer: string;
  sources: Array<{
    title: string;
    source?: string;
    date?: string;
    person?: string;
    url?: string;
    drive_link?: string;
  }>;
};

export async function queryMemory(input: RagQuery, ragToken: string) {
  // Use /api/rag/query only if the frontend proxy adds the /api prefix.
  const response = await fetch("/rag/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-RAG-Token": ragToken,
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<RagResponse>;
}
```

For a production dashboard, do not expose `RAG_QUERY_TOKEN` to browser JavaScript. Put the request behind a server-side dashboard route that authenticates the current user and supplies the workspace ID from the session. The current token-protected endpoint is intended for local/admin testing only.

## 6. Curl test for Gemini RAG

Start the backend and configure a local test token:

```bash
cd sera/backend
export RAG_QUERY_TOKEN="replace-with-a-long-random-local-token"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Set the workspace UUID that owns the connected data. It can be read from your development database; never guess or use another user’s workspace. Then query all indexed sources:

```bash
export WORKSPACE_ID="00000000-0000-0000-0000-000000000000"

curl -sS -X POST http://127.0.0.1:8000/rag/query \
  -H "Content-Type: application/json" \
  -H "X-RAG-Token: $RAG_QUERY_TOKEN" \
  -d @- <<JSON
{
  "workspace_id": "$WORKSPACE_ID",
  "question": "What did we decide about the payment API migration?"
}
JSON
```

To restrict retrieval to one source label, pass `source_types`. The label must match the ingestion metadata exactly:

```bash
curl -sS -X POST http://127.0.0.1:8000/rag/query \
  -H "Content-Type: application/json" \
  -H "X-RAG-Token: $RAG_QUERY_TOKEN" \
  -d "{\"workspace_id\":\"$WORKSPACE_ID\",\"question\":\"What did Slack say about the release?\",\"source_types\":[\"Slack\"]}"
```

A successful response looks like this:

```json
{
  "answer": "The team decided to migrate the payment API before the next release.",
  "sources": [
    {
      "title": "#engineering",
      "source": "Slack",
      "date": "2026-08-25",
      "person": "Rahul",
      "url": "https://app.slack.com/..."
    }
  ]
}
```

## 7. Python test script

The repository includes `backend/scripts/query_rag.py`, which uses only Python’s standard library:

```bash
cd sera/backend
export RAG_QUERY_TOKEN="replace-with-a-long-random-local-token"
python scripts/query_rag.py \
  --workspace-id "$WORKSPACE_ID" \
  "Summarize the latest decision about Project Alpha"
```

Use `--source` more than once to compare sources:

```bash
python scripts/query_rag.py \
  --workspace-id "$WORKSPACE_ID" \
  --source "Slack" \
  --source "Google Calendar" \
  "What changed between the Slack discussion and the scheduled meeting?"
```

The script prints the answer followed by each returned citation. A `401` means the header token is wrong, a `503` means `RAG_QUERY_TOKEN` is not configured, and a no-context answer means no indexed chunk cleared the configured similarity threshold.

## 8. Telegram inline connector menu

The backend now exposes `/connect`, which renders inline buttons for Google, Maps, Notes, Slack, Teams, Discord, LinkedIn, Reddit, X/Twitter, and Facebook. The callback handler uses these rules:

| Button | Behavior |
|---|---|
| Google provider | Creates one-time OAuth state and shows **Continue with Google**. |
| Slack | Creates Slack OAuth state and shows **Continue setup in Slack**. |
| Teams | Creates Microsoft OAuth state and shows **Continue setup in Teams**. |
| Google Maps | Reports whether `GOOGLE_MAPS_API_KEY` is configured; it does not start OAuth. |
| Google Notes | Starts the read-only Keep OAuth flow and explains Workspace admin approval. |
| Social foundation | Explains that provider-specific OAuth/app review is not enabled yet and does not create a fake connection. |

The bot registers `CallbackQueryHandler` for callback data matching `setup:<provider>`. Keep callback provider names allowlisted; never use arbitrary callback data to select a connector or workspace.

Users can now use:

```text
/connect
/status
/connections
```

## 9. Verification checklist

After adding the dashboard, verify that catalog foundation cards are not rendered as connected, no token is present in browser logs, OAuth redirects preserve the initiating user, Maps is represented as API-key configuration, and RAG answers show source citations. Run the backend checks before committing:

```bash
cd sera/backend
python3 -m compileall -q app alembic scripts
pytest -q
git diff --check
alembic heads
```

The current backend test suite covers OAuth, provider parsing, catalog boundaries, RAG isolation/provider filtering, and work-intelligence metrics. Live connector testing still requires the corresponding Google, Slack, Microsoft, Maps, Gemini, Telegram, and database credentials.
