# SERA Frontend, Telegram Workers, and Vector RAG Guide

## 1. Run the React dashboard

The repository now contains a Vite + React + TypeScript starter in `frontend/`. It renders a SERA-style workspace overview with connection cards, Google Maps/Notes and social connector states, work-detective patterns, and a Memory Search screen.

```bash
cd sera/frontend
pnpm install
pnpm dev
```

Open `http://localhost:5173`. The Vite proxy forwards `/connectors`, `/rag`, and `/oauth` requests to the FastAPI service at `http://127.0.0.1:8000`.

Build a production bundle with:

```bash
pnpm build
pnpm preview
```

The dashboard intentionally uses realistic fallback catalog data when the backend is unavailable, so the UI can be reviewed before credentials and database setup are complete. The current backend does not yet expose a browser session-authenticated workspace-status route. Before production, add that route and replace the placeholder workspace ID in `src/App.tsx` with the server-side session’s workspace ID. Never put `RAG_QUERY_TOKEN`, OAuth client secrets, or provider access tokens into browser JavaScript.

## 2. Dashboard component boundaries

The starter separates provider discovery from connection state. `ConnectionGrid` renders the `/connectors/catalog` response, `ConnectorCard` maps capability/status fields to setup actions, `MemoryPanel` calls `/rag/query` through a future authenticated dashboard proxy, and `DetectivePanel` is the first visual surface for repeated-work candidates.

| State | UI treatment |
|---|---|
| `connected` | Green badge, last-sync timestamp, and “Manage connection”. |
| `pending` | Amber badge and “Continue setup”. |
| `needs_reauth` | Warning badge and “Reconnect”. |
| `implemented_foundation` | “Configure” with provider limitation. |
| `catalog_foundation` | Disabled action explaining that provider OAuth/app approval is still required. |

Google Maps is represented as API-key configuration rather than account OAuth. Google Notes/Keep is shown as Workspace-admin-gated. Social catalog providers remain explicit foundations until their real provider-specific app and permissions are implemented.

## 3. Local Telegram and API processes

The FastAPI process can still run Telegram polling and scheduling together for the simplest local setup:

```bash
cd sera/backend
cp .env.example .env
# keep START_TELEGRAM_IN_WEB=true and START_SCHEDULER_IN_WEB=true
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For a durable deployment, run the API, Telegram bot, and sync scheduler as separate processes. Set these values in `.env` for the API process:

```dotenv
START_TELEGRAM_IN_WEB=false
START_SCHEDULER_IN_WEB=false
```

Then start the three processes:

```bash
# Terminal 1: API and OAuth callbacks
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Telegram long-polling worker
python -m app.bot_worker

# Terminal 3: periodic connector sync worker
python -m app.worker
```

Do not run embedded polling/scheduling and dedicated workers at the same time. Otherwise Telegram updates can be consumed by two bot processes and scheduled jobs can run twice. Store state in PostgreSQL, not process memory, so worker restarts remain safe.

For production, supervise each process with Docker Compose, systemd, or a managed always-on service. The backend’s `app.worker` entrypoint keeps the scheduler alive and `app.bot_worker` owns long polling. The sync interval is controlled by `DRIVE_SYNC_INTERVAL_MINUTES`; the same scheduler dispatches Drive, Gmail, Calendar, Meet, Keep, Slack, and Teams connectors.

## 4. Realtime Telegram notifications

OAuth callbacks may run in the API process while Telegram polling runs in another process. SERA therefore has a direct Bot API fallback in `app/services/notifications.py`. After a successful connector callback and initial sync dispatch, SERA sends the user a connection/sync notification even when the in-process Telegram bot registry is unavailable.

Use this notification pattern for user-visible events:

| Event | Notification behavior |
|---|---|
| OAuth completed | Notify immediately that the provider is connected and indexing has started. |
| Initial sync finished | Send one summary with provider name and indexed record count when the sync function exposes a count. |
| Re-authentication required | Send one actionable message with the relevant `/connect_<provider>` command. |
| Periodic sync | Do not send a message on every successful polling cycle; notify only on new important items, failures, or a user-configured digest. |
| Automation candidate discovered | Send a review prompt and require explicit approval before any external write action. |

Keep notifications idempotent. Persist an event key such as `(connector_id, event_type, external_id)` before sending or use an outbox table if delivery guarantees matter. Never include access tokens or full private message content in notification logs.

## 5. Chunking and Gemini embeddings

SERA chunks every indexed document before embedding. The default rough boundary is 500 tokens with 50-token overlap, using a word-based heuristic suitable for the MVP. Configure it with:

```dotenv
CHUNK_SIZE_TOKENS=500
CHUNK_OVERLAP_TOKENS=50
GEMINI_EMBED_MODEL=text-embedding-004
```

`app/services/ingestion.py` now creates deterministic chunk records, embeds each chunk with the existing Gemini embedding service, stores the chunk in PostgreSQL/pgvector, and optionally mirrors the same record to Chroma or Pinecone. Upserts use stable chunk/document metadata and stale vectors are removed on document replacement where the configured vector store supports metadata deletion.

Keep document metadata on every vector record: `workspace_id`, `document_id`, `source`, `title`, `url`, and the internal chunk ID. This is required for tenant isolation, source filtering, and citation reconstruction.

## 6. Choose a vector backend

PostgreSQL/pgvector remains the default and requires no additional vector package:

```dotenv
VECTOR_STORE_BACKEND=pgvector
```

For local persistent Chroma:

```bash
cd sera/backend
pip install -r requirements-vector.txt
```

```dotenv
VECTOR_STORE_BACKEND=chroma
CHROMA_PERSIST_DIR=./.chroma
CHROMA_COLLECTION_NAME=sera_chunks
```

SERA uses a persistent Chroma client, a collection with cosine distance, explicit Gemini vectors, workspace metadata, `upsert`, metadata deletion, and query. Chroma’s in-memory client loses data when the process exits; use a persistent client or server for durable storage [1](https://docs.trychroma.com/docs/overview/getting-started).

For Pinecone:

```bash
cd sera/backend
pip install -r requirements-vector.txt
```

```dotenv
VECTOR_STORE_BACKEND=pinecone
PINECONE_API_KEY=your-server-side-key
PINECONE_INDEX_HOST=your-index-host
PINECONE_NAMESPACE=sera
```

Create the Pinecone index with a **768-dimensional cosine metric** to match the current Gemini `text-embedding-004` model output. SERA targets the index by host, uses a namespace, upserts dense vectors with metadata, deletes by workspace/document metadata, and queries with a workspace/source filter. Pinecone recommends targeting an index by its unique host in production rather than resolving by index name on every request [2](https://docs.pinecone.io/guides/manage-data/target-an-index). Namespaces and metadata filters should be used for tenant isolation [3](https://docs.pinecone.io/guides/index-data/upsert-data).

Do not enable both external stores for the same environment unless you intentionally want dual writes. The supported backend choices are one of `pgvector`, `chroma`, or `pinecone`.

## 7. Multi-source Gemini RAG flow

The retrieval path is:

```text
Provider sync
  → normalized document
  → configurable chunks
  → Gemini embedding
  → pgvector / Chroma / Pinecone
  → workspace + source-filtered retrieval
  → Gemini answer from retrieved text
  → deduplicated citations + query log
```

`query_connected_sources()` automatically selects the configured vector backend. With `pgvector`, it performs SQL cosine-distance retrieval. With Chroma or Pinecone, it queries the external store, fetches the matching internal `Chunk` rows by UUID, applies the similarity floor, and reconstructs the same source citations. That internal fetch prevents external metadata from bypassing the workspace boundary.

Gemini embeddings are used for semantic retrieval; the question and indexed chunks must use the same embedding model and compatible vector dimension. Google’s embedding documentation describes embeddings as vectors for semantic search and supports controlling output dimensionality for compatible models [4](https://ai.google.dev/gemini-api/docs/embeddings).

## 8. Test the vector/RAG path

Run the default backend tests and frontend build:

```bash
cd sera/backend
python3 -m compileall -q app alembic scripts
pytest -q

cd ../frontend
pnpm build
```

For a live local RAG query, configure `RAG_QUERY_TOKEN`, start the API, and use the repository client:

```bash
cd sera/backend
export RAG_QUERY_TOKEN="local-long-random-token"
export WORKSPACE_ID="your-workspace-uuid"
python scripts/query_rag.py \
  --workspace-id "$WORKSPACE_ID" \
  "What did we decide about Project Alpha?"
```

When using Chroma or Pinecone, verify that the vector dimension matches the Gemini embedding model, that the workspace metadata filter is present, and that a document update does not leave stale external matches. Keep this endpoint local/admin-only until it is placed behind real web-session authentication.

## References

[1]: https://docs.trychroma.com/docs/overview/getting-started "Chroma Getting Started"
[2]: https://docs.pinecone.io/guides/manage-data/target-an-index "Pinecone Target an Index"
[3]: https://docs.pinecone.io/guides/index-data/upsert-data "Pinecone Upsert Records"
[4]: https://ai.google.dev/gemini-api/docs/embeddings "Gemini API Embeddings"
