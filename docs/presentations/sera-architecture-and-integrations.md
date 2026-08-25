# SERA — Architecture, Dashboard & Connected Intelligence

## Cover
**SERA**  
Your AI work memory that learns how you work

Architecture, secure dashboard, vector RAG, and integrations

## Slide 1
**The product thesis: remember more, repeat less**

- SERA is not just a chatbot; it builds a living memory of work and life context.
- It answers “What happened?” with evidence and asks “What should never be manual again?”
- Core loop: **Remember → Understand → Detect → Automate**.

## Slide 2
**One intelligence layer across fragmented work**

- Sources: Gmail, Drive, Calendar, Meet, Slack, Teams, Notes, and future social connectors.
- A normalized memory layer turns messages, documents, meetings, transcripts, and events into searchable context.
- Human approval remains the boundary before external actions are executed.

## Slide 3
**Telegram-first, web-ready product architecture**

- Telegram is the first conversational surface for onboarding, account linking, status, insights, and `/ask`.
- FastAPI owns OAuth callbacks, encrypted credentials, ingestion, retrieval, Gemini reasoning, and scheduled sync.
- The React dashboard is the visual command center for connections, memory search, and Work Detective insights.
- PostgreSQL keeps users, workspaces, connectors, meetings, documents, chunks, sessions, and query logs durable.

## Slide 4
**Security is built into the connection boundary**

- Google login creates a verified identity and a server-side workspace session.
- The browser receives only an opaque, `HttpOnly`, `SameSite` cookie; the raw session token is never stored in the database.
- Workspace ID is derived server-side from the session, not accepted from browser query payloads.
- OAuth state is short-lived and one-time; provider tokens are encrypted at rest.

## Slide 5
**The dashboard makes connected context legible**

- Connection cards show status, capability, setup mode, sync state, and provider limitations.
- “Continue setup” routes through the backend so OAuth state and consent stay server-controlled.
- Memory Search uses the authenticated proxy and returns source citations instead of an opaque answer.
- Work Detective is designed to turn repeated activity into reviewable automation candidates.

## Slide 6
**Documents become retrieval-ready memory**

- Provider sync normalizes raw content into documents with source, title, date, person, URL, and connector metadata.
- Configurable chunking defaults to 500-token chunks with 50-token overlap.
- Gemini embeddings represent chunks semantically for cross-source search.
- Re-indexing removes stale vectors and mirrors the same metadata across the selected vector backend.

## Slide 7
**One RAG contract, three deployment choices**

- Default: PostgreSQL + pgvector for a simple, workspace-local deployment.
- Local/private option: persistent Chroma collection with cosine retrieval and metadata filters.
- Managed scale option: Pinecone host + namespace + workspace metadata filters.
- Retrieval always re-fetches internal chunk rows by ID before Gemini generation, preserving tenant isolation.

## Slide 8
**From question to cited Gemini answer**

- User asks in Telegram with `/ask` or uses Memory Search in the dashboard.
- SERA embeds the query, retrieves across permitted connected sources, applies workspace/source filters, and enforces a similarity floor.
- Gemini receives only the retrieved context and produces the answer.
- The response includes deduplicated citations and is recorded in the query log for traceability.

## Slide 9
**Integrations are staged by capability and consent**

- Implemented: Google Drive, Gmail, Calendar, Meet, Slack, and Microsoft Teams read-oriented sync foundations.
- Google Maps uses a restricted server-side Places API key, not user account OAuth.
- Google Notes/Keep is an admin-gated Workspace connector rather than a guaranteed consumer feature.
- Discord, LinkedIn, Reddit, X/Twitter, and Facebook are catalog foundations until provider-specific apps, scopes, reviews, and rate limits are configured.

## Slide 10
**Background workers keep memory current**

- API process handles web sessions and OAuth callbacks.
- Telegram worker owns long polling and conversational notifications.
- Sync worker runs incremental connector jobs on a durable interval.
- Deployment flags prevent duplicate polling and duplicate scheduled sync when processes are split.

## Slide 11
**The product flywheel gets stronger with use**

- More connected context improves answers and source-grounded memory.
- Repeated actions become measurable Work Events with frequency, first/last detection, average duration, and time cost.
- Approved candidates become workflow definitions, not silent automations.
- The system evolves from “search what happened” to “show me what I should stop doing.”

## Slide 12
**The next milestone: safe action execution**

- Complete web session UX with live sync counters, re-authentication, and user-configured source filters.
- Add an outbox/notification layer for reliable event delivery and non-noisy sync digests.
- Add provider-specific social connectors only after scope and review validation.
- Execute approved workflows through audited, reversible actions with clear user confirmation.
