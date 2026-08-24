# Sera — AI Operating System for Work
### Product Requirements Document (PRD)

> "Understands. Remembers. Reasons. Acts."
> Your data. Your workspace. Your AI.

Consolidated from: `index.txt`, `index1.txt`, `image.png` (architecture poster), `logo.png` / `logo_descriptive_img.png` (brand).

---

## 1. Vision

Build an **AI Operating System for Knowledge Work** — not another chatbot, but a platform where a user connects all of their digital tools (Slack, Gmail, Google Drive, Notion, GitHub, Zoom, Calendar, Teams, ChatGPT, Claude, Gemini, Google Notes, Dropbox, etc.) and an AI layer continuously understands, searches, organizes, remembers, and eventually **acts** on their behalf.

**Long-term vision statement:** *To become the AI Operating System for every individual and organization — where AI understands your work, remembers everything important, proactively helps you, and safely gets things done with your permission.*

Positioning reference points: Microsoft Copilot, Google Gemini Workspace, Glean, Notion AI. Differentiation: user-controlled workspaces, multi-source retrieval, strong source attribution, modular connectors, multi-agent architecture.

---

## 2. Problem Statement

Today a user's information is scattered across many disconnected tools:

- Slack, Gmail, Google Drive, Notion, meeting recordings, documents, GitHub, Zoom/Teams, Calendar, ChatGPT / Claude / Gemini history, Google Notes.

This leads to lost context and repeated questions such as:
- What was decided in yesterday's meeting?
- Who promised to do what?
- Where is that API document?
- What did my manager say about the deadline?
- What did I ask ChatGPT last month about X?

There is no single place that unifies conversations, documents, decisions, and tasks with trustworthy, cited answers.

---

## 3. Product Goal

Create **one workspace** where a user (or team) can ask natural-language questions and get accurate, **source-cited** answers pulled from every connected tool — and, later, have the AI take safe, user-approved actions across those tools.

Example interaction:

```
User: What happened in today's meeting?

AI: Today's Backend Team Meeting
    Summary: The team decided to migrate authentication
    from session-based auth to JWT.

    Key decisions:
    1. JWT migration starts next sprint
    2. Database schema remains unchanged

    Action Items:
    John  – Create migration plan (Deadline: Friday)
    Sarah – Update API documentation

    Sources:
    ✓ Slack #backend-team — message from John, 10:42 AM
    ✓ Google Meet transcript — Backend Sync, July 27
    ✓ Notion document — Auth Migration Plan
```

**Source citation is a first-class requirement, not an afterthought** — every answer must be traceable back to the exact message, document, or transcript segment it came from.

---

## 4. Core Product Principles

1. **You own your data** — user-controlled workspaces, not a black box.
2. **Every answer is cited** — no hallucinated claims; always show source, date, author, link.
3. **Multi-source reasoning** — one question can pull from Slack + Gmail + Meeting + Docs simultaneously.
4. **Consent-based memory and actions** — AI only remembers preferences and takes actions with explicit user approval.
5. **Modular connectors** — each integration (Slack, Gmail, Drive, etc.) is an independent, pluggable connector.
6. **Multi-agent architecture** — specialized agents (not one monolithic prompt) collaborate under a supervisor/orchestrator.

---

## 5. Competitive Positioning & Differentiation Risk

**The risk:** ChatGPT, Claude, and Gemini are all shipping native "connect your apps" features (Gmail, Drive, Slack, Notion, etc.). If Sera's pitch is "we connect your tools," that pitch has a short shelf life — the incumbents will commoditize plain connectors faster than a small team can out-integrate them.

**What actually stays defensible:**
1. **Cross-source, cross-assistant reasoning** — Sera is the one place that can answer using Slack *and* Gmail *and* what you asked ChatGPT *and* what you asked Claude *and* your meeting notes, together, in one cited answer. No single AI vendor will unify its competitors' chat histories — that neutrality is structurally only possible outside of any one of them.
2. **Persistent, workspace-scoped memory that outlives any single chat session** — ChatGPT/Claude connectors search live within *their own* conversation; they don't build a durable, queryable knowledge base with citations that a team can share and audit over time.
3. **Source-grounded, auditable answers** — evidence-per-claim with timestamps/links is a trust feature enterprises need and generic assistant connectors don't prioritize.
4. **Workspace/team ownership model** — multi-user roles, shared knowledge base, org-level control — a product surface, not a personal chat feature.

**Implication for scope:** Don't market or build toward "we have the most connectors." Build toward "we're the one memory layer that sits above every assistant and every tool you use, with proof for every answer." Connector breadth (Section 10.5) is plumbing in service of that, not the pitch itself.

**MVP scoping risk:** the 6-phase / 40-agent roadmap (Sections 10.3, 14) is large for a small team. Recommend picking one narrow wedge first (e.g., meeting + decision tracking for a small team, Section 8.1–8.4) and shipping it well before generalizing across all connectors and all phases — a big roadmap that never ships loses to a narrow one that does.

---

## 6. Target Users

- Individuals wanting a personal "second brain" over their own digital life (personal workspace).
- Teams / startups wanting a shared knowledge base across Slack, GitHub, Notion, Zoom (team workspace).
- Researchers / students organizing papers, PDFs, and notes (research workspace).
- Enterprises eventually — with RBAC, permissions, audit logs, compliance (Phase 6).

A single user can own **multiple workspaces** (e.g., Personal, Startup, Freelancing, College, Research), each with its own connected apps, and switches between them via a workspace selector. Search and memory are always scoped to the **current workspace**.

---

## 7. User Journey

**Step 1 — Sign Up**
Email, Password, Workspace Name → Create Workspace.

**Step 2 — Connect Applications**
Checklist of connectors: Gmail, Slack, Google Drive, Dropbox, Notion, Google Notes, Discord, GitHub, ChatGPT, Claude, Gemini, Teams, Zoom, Calendar.
- Click "Connect Gmail" → Google OAuth → grant permission → done.
- Click "Connect Slack" → Slack OAuth → done.
- Click "Connect Claude / Gemini" → provider OAuth or API key → conversation history synced → done.

**Step 3 — Live Workspace Dashboard**
Shows connected apps, last sync time per source, documents indexed, messages indexed, embeddings count.

**Step 4 — Ask Anything**
User queries the workspace in natural language (text or voice) and gets a cited answer.

**Step 5 (later) — Approve Actions**
AI proposes an action (send email, create doc, schedule meeting); user confirms before execution.

---

## 8. Feature Set

### 8.1 MVP (Version 1 / Phase 1)
- Upload PDF documents, meeting transcripts, notes.
- Chunk + embed + store in vector DB.
- Ask questions, get answers with citations.
- Basic chat interface.
- Single user, single workspace.

### 8.2 Connected Knowledge (Version 2 / Phase 2)
- Gmail, Google Drive, Slack, Notion connectors.
- OAuth-based auth per connector.
- Incremental / scheduled sync (new messages/files only, not full re-index).

### 8.3 Collaboration (Phase 3)
- Multiple workspaces per user.
- Team members and roles (Owner, Admin, Editor, Viewer).
- Shared knowledge base within a workspace.
- Workspace-level permissions.

### 8.4 AI Memory & Intelligence (Version 3 / Phase 4)
- Personal memory / preferences (opt-in): e.g. "John prefers FastAPI", "usually writes Python", "working on Payment API".
- Daily Briefing: morning summary of yesterday's Slack conversations, meetings, and document updates, plus important flagged changes.
- Decision Tracker: AI automatically extracts decisions made, who made them, and the source.
- Personal Search Engine: Google-like search across all connected sources ("authentication issue" → Slack, meeting transcript, GitHub discussion).
- Meeting summaries, task/action-item extraction, timeline/history features, workspace replay.
- Cross-source search and reasoning.

### 8.5 Proactive AI Action Platform (Phase 5)
AI can **perform actions** with explicit user approval:
- Summarize today's emails → read Gmail → summarize → send report.
- Find all invoices → search Gmail + Drive → create spreadsheet.
- Prepare tomorrow's meeting → read calendar → find related Slack threads/docs → generate briefing.
- Draft email/Slack replies (shown for approval before sending).
- Smart notifications, workflow automation, calendar scheduling, safe execution with rollback/audit logging.

### 8.6 Enterprise AI OS (Phase 6)
- Multi-workspace + org-wide RBAC and permissions.
- SSO & compliance.
- Org-wide memory & analytics.
- Marketplace & public APIs.

### 8.7 Interface Layer (per architecture poster)
- **Telegram** — native/available first.
- Voice, Web App, Mobile App, API/SDK, Desktop/VS Code — future interfaces.
- All interfaces share one backend platform and one memory ("One Intelligence. Every Interface.").

### 8.8 Autonomous Agent Mode (Manus-style)

Sera isn't only a "ask and get an answer" tool — it also runs **self-triggered, autonomous work** the way agent products like Manus do: the AI initiates a task on its own (on a schedule or trigger), does multi-step work across connected sources, and delivers a finished result — without the user having to ask each time.

**What this means concretely:**
- **Daily Briefing** (Section 8.4) is the first instance of this: every morning, without being asked, Sera reads yesterday's activity across all connected sources and delivers a ready summary.
- The same pattern generalizes to other autonomous runs: weekly digests, pre-meeting prep ("read Calendar → find related Slack threads/docs → generate briefing", Section 8.5), decision/task tracking updates, and follow-up reminders — all fired by a schedule or an event (e.g., "new meeting added to Calendar"), not by a user prompt.
- **Multi-step, tool-using execution**: like Manus, a triggered run can chain multiple actions (search → read → summarize → draft → notify) end-to-end in one autonomous pass, using the Agent Orchestration Layer and Action Orchestrator (Section 10.2).
- **Still governed by the same safety model**: read-only autonomous runs (briefings, summaries, tracking) can deliver directly; anything that writes or sends externally (email, Slack message, calendar invite) still goes through the Action Execution Flow's user-confirmation step (Section 10.8) — autonomy applies to *when work starts and how many steps it chains*, not to bypassing approval for external-facing actions.
- **User control:** each autonomous routine can be enabled/disabled per workspace, with its own schedule/trigger and a visible run log (what ran, when, what it touched, what it produced) — this is what makes "the AI is now doing things on its own" trustworthy rather than opaque.

This is a distinct capability from the RAG-based Q&A flow (Section 10.7): Q&A answers a question *you* ask; Autonomous Agent Mode produces a deliverable *before* you ask, and is where Sera most directly resembles Manus-style autonomous agents rather than a search/chat assistant.

---

## 9. Key Differentiators

- Telegram-native first.
- Hybrid query modes: General knowledge + Workspace-specific + Hybrid (combine both).
- Multi-agent AI architecture (40+ specialized agents across 8 teams).
- Real-time sync and proactive AI (not just reactive Q&A).
- Source citation with evidence on every answer.
- Privacy, security, and full user data ownership.
- Enterprise-ready from day one (permissions, audit, compliance groundwork).
- Multi-language and voice AI experience.

---

## 10. System Architecture

### 10.1 High-Level Flow
```
User
 │
Ask Question
 │
AI Workspace API
 │
Query Orchestrator
 │
 ├── Retriever ──── Vector Database ──── Metadata Store ──── Connectors
 └── LLM
```

### 10.2 Cognitive Architecture ("AI Brain")
| Component | Responsibility |
|---|---|
| Query Router | Intent detection; routes to Workspace / General / Hybrid; action vs. agent selection; language understanding |
| Supervisor Agent (Chief Orchestrator) | Plans and breaks down tasks; chooses agents; manages context; ensures safety; tracks execution |
| Memory & Context (Workspace Understanding) | Long-term memory; user preferences; workspace "DNA"; context window management; history & continuity |
| Agent Orchestration Layer | Coordinates all agents; shares context; manages memory; executes plan; handles dependencies |
| Response Composer | Synthesizes final answer; adds citations; formats for interface; language translation; confidence score |
| Action Orchestrator (Safe Execution) | Approval & confirmation; executes actions; monitor & retry; rollback/error handling; audit logs |

### 10.3 AI Agent Ecosystem (40+ agents across 8 teams)
| Team | Example Agents |
|---|---|
| Executive (Strategy & Control) | Supervisor, Planner, Orchestrator |
| Knowledge (Memory & Search) | Memory, Search, Timeline, Decision, Citation, Knowledge Graph |
| Integration (Connect & Sync) | Connector, Sync, OAuth, File Processing, Deduplication |
| Productivity (Work Intelligence) | Meeting, Daily Briefing, Task, Calendar, Workspace Health |
| Conversation (Chat & Voice) | Chat, Voice Intelligence, Translation, Conversation Memory |
| Action (Do & Automate) | Email, Message, Workflow, Approval, Automation |
| Enterprise (Security & Governance) | Permission, Security, Compliance, Audit, Policy |
| Intelligence (Learning & Insights) | Insight, Recommendation, Conflict Detection, Learning, Pattern Detection |

### 10.4 Knowledge Platform (Organizational Memory)
```
User Data (Encrypted)
   → Processing Pipeline (Chunking, OCR, Parsing, Metadata)
   → Knowledge Graph (Entities, Relations) ── Relational DB (PostgreSQL)
   → Vector Layer (Embeddings) ── Cache Layer (Redis) ── Object Storage (S3/MinIO)
```
Capabilities: semantic search, hybrid search (vector + keyword), reranking & scoring, deduplication, entity extraction, PII detection, summarization, versioning, access control.

### 10.5 Connectors & Sync Engine
Supported sources: Gmail, Google Drive, Slack, Telegram history, Notion, Google Notes, Teams, Calendar, ChatGPT, Claude, Gemini, local folder/PDF, and more.

Each connector follows the same pipeline shape:
```
<Source API> → Raw content → Cleaning → Chunking → Embedding → Vector DB
```

Concrete examples:
- **Slack Connector:** Slack API → Messages → Cleaner → Chunking → Embedding → Vector DB.
- **Gmail Connector:** OAuth → Emails → Attachments → Cleaning → Embedding → Vector DB.
- **Google Drive:** Drive → PDF/Word/Excel → Extract Text → Chunk → Embed.
- **Zoom:** Meeting → Recording → Transcript → Chunks → Embedding.
- **GitHub:** Repository → Issues → PRs → Comments → Embedding.
- **ChatGPT / Claude / Gemini history:** Conversation → Messages → Embedding → Workspace (so past AI-assistant chats become searchable too).
- **Google Notes:** Note → Text/Checklist → Cleaning → Chunking → Embedding → Vector DB.

Sync behavior: real-time/scheduled sync, selective source scoping, change detection, chunking & embedding, error handling & retry, webhooks/push (future). Incremental daily indexing embeds **new messages only**, not a full re-embed.

### 10.6 Stored Data Shape (per chunk)
Every piece of content is stored with metadata enabling attribution:
```json
{
  "text": "Meeting decided to use PostgreSQL",
  "source": "Google Meet",
  "date": "2026-07-27",
  "person": "John",
  "url": "meeting-link"
}
```
Similarly for Gmail (subject, sender, thread ID, workspace), Slack (channel, message ID, time, author, workspace), Claude/Gemini/ChatGPT (conversation ID, title, timestamp, workspace), Google Notes (note ID, title, timestamp, workspace).

### 10.7 End-to-End Query Flow (Search)
```
User Query (Text/Voice)
   → Gateway/Auth Layer
   → Query Router (General / Workspace / Hybrid)
   → Agent Selection
   → Search Engine
   → Embedding
   → Vector Search
   → Top 20 Results
   → Reranking
   → Top 5
   → LLM (Answer Generation)
   → Response Composer
   → Interface Response
   → Feedback Loop (continuous improvement)
```
- **General mode:** uses world knowledge (e.g., "What is Kubernetes?").
- **Workspace mode:** searches only connected sources (e.g., "What happened in yesterday's meeting?").
- **Hybrid mode:** combines both for richer answers (e.g., "We decided to use pgvector, explain it in detail").

#### 10.7.1 RAG Maturity Roadmap

The retrieval layer is built in stages, not all at once — each stage ships and is proven before the next is added:

1. **Basic RAG** *(current MVP — implemented)*: embed question → single pgvector similarity pass → similarity-threshold filter → single LLM call → cited answer. No re-ranking, no iteration.
2. **Advanced RAG**: re-ranking, hybrid search (vector + keyword), query rewriting/expansion, improved chunking.
3. **Agentic RAG**: multi-step reasoning — query decomposition, iterative re-retrieval, self-critique before answering. This is where the flow above (Top 20 → Reranking → Top 5) and the Deep Research pipeline (Section 8.4/8.8, and the decompose → search → cross-verify → synthesize pattern) actually get built.
4. **Multilingual RAG**: dedicated multilingual embedding/translation layer (the MVP's embedding model is English-primary).
5. **Graph RAG**: retrieval backed by the Knowledge Graph (Section 10.4).
6. **Multimodal RAG**: images and other non-text content (OCR/scanned documents are explicitly out of scope for the MVP).
7. **RAG Evaluation**: a systematic eval harness — retrieval accuracy, citation accuracy, hallucination rate — so later stages are measured against a baseline, not judged by feel.
8. **Production RAG**: caching, cost controls, monitoring/observability, and scale hardening (ties into Section 15's cost-control architecture).

**Guidance:** don't jump ahead to a later stage until the current one is proven end-to-end — the same "ship the narrow slice first" principle as the rest of the roadmap (Section 14).

### 10.8 Action Execution Flow (Safe & Confirmed)
```
User Requests Action
   → Action Planner Agent
   → Prepare Action
   → Show & Get Confirmation
   → User Confirms? ── No → Cancel Action
                      └ Yes → Execute Action → Log & Notify
```
Every AI-initiated action (send email, draft reply, create doc) requires explicit user confirmation before execution, and is logged/audited afterward.

### 10.9 Web-First vs. Desktop Architecture (Decision)

**Decision: Sera is web-first, not a desktop application.** This was evaluated directly against OpenHuman (React UI + Tauri + Rust core, desktop-only — no supported standalone web client) and rejected as a model to copy, because Sera's use case (background jobs, connectors, scheduling) doesn't need the local machine to be part of the architecture.

```
WEB APP
   │
   ↓
CLOUD BACKEND (API)
   │
   ↓
JOB QUEUE
   │
   ↓
AGENT WORKER
   │
   ↓
CONNECTORS
```

- The browser (or Telegram, or any future client) is a **control panel**, not the execution engine. All heavy work — agent orchestration, research, background jobs, scheduling, connector calls, memory, approval state — runs server-side.
- Because execution is server-side, a job survives the user closing the browser, and the same in-progress job is viewable from laptop → phone → tablet (or Telegram) without restarting.
- **Exception:** if Sera later needs *local computer-use* (e.g. "open VS Code on my machine and do X"), a pure web app isn't enough — the browser can't get arbitrary OS access. That would require an optional **Desktop Companion / local agent** as a later add-on (Phase 3+), not a redesign of the core, which stays: `Cloud Backend → Job → { Cloud Tools | Local Agent }`.
- This is a deliberate divergence from OpenHuman's architecture, which is intentionally built around a Tauri desktop shell — Sera's web-first choice is what makes the multi-interface Job Engine model (Section 10.10) possible.

### 10.10 Job Engine — Multi-Interface Abstraction

The unit of work in Sera is a **Job**, and every interface is just a different entry point into the same Job Engine — this is what lets Telegram (Section 8.7) become a first-class interface without duplicating the agent runtime.

```
                YOUR AI
                   │
             ┌─────┴─────┐
             │ JOB ENGINE │
             └─────┬─────┘
                   │
     ┌─────────────┼─────────────┐
     ↓             ↓             ↓
    Web        Telegram        Future
    UI           Bot        (WhatsApp, Voice,
     │             │          Desktop Agent)
     └─────────────┼─────────────┘
                   ↓
            SAME JOB SYSTEM
                   │
     ┌─────────────┼─────────────┐
     ↓             ↓             ↓
  Research     Connectors     Actions
```

Example: a job started with a Telegram command ("Research the top 10 competitors and prepare a comparison by tonight") is assigned a job ID, runs through the same Research → Web Search → Analyze → Report pipeline as a web-initiated job, and can complete with a Telegram notification (`Job #124 completed ✅ [View Report]`) while remaining visible/resumable in the web dashboard. Anything requiring external-facing permission still surfaces an **Approval required** prompt (Section 10.8) regardless of which interface started the job.

**Architectural implication:** the agent runtime must never assume "web" as its caller — job state, progress, and approval prompts are interface-agnostic, and each interface (web, Telegram, future channels) is a thin adapter that renders the same job state and forwards the same actions.

### 10.11 Illustrative Usage Examples
1. **"Give me today's meetings"** (Telegram/Voice) → Router → Workspace Query → Agents search Calendar/Slack/Email/Docs → answer lists meetings with times, cites Google Calendar, Slack thread, Drive doc.
2. **General knowledge query** (outside workspace) → Router → General Query → LLM/Web Search → cites external web sources (e.g. ESPN Cricinfo).
3. **Decision discovery** (multi-source reasoning) → "What did John decide about Payment API?" → Router → Workspace Query → Agents search Slack, Meeting Notes, Email → single synthesized answer with evidence timestamps from all three sources.
4. **Action example** (safe & confirmed) → "Reply to John that deployment is complete" → Action Agent drafts reply → shown to user → user Sends or Cancels.
5. **Voice interaction** (future) → Voice query → STT → Router & Agents search/reason → TTS voice response, with source shown (e.g., Google Calendar).

---

## 11. Data Model (Suggested Schema)

```
Users
  id, name, email

Workspaces
  id, owner_id, name, description

WorkspaceMembers
  workspace_id, user_id, role   # Owner / Admin / Editor / Viewer

Connectors
  workspace_id, provider, status, oauth_token, last_sync

Documents
  id, workspace_id, connector_id, title, type, metadata

Chunks
  id, document_id, text, embedding, metadata

ChatHistory
  workspace_id, conversation, summary

Tasks
  workspace_id, title, status, source, assigned_to
```

---

## 12. Recommended Tech Stack

**Frontend**
- Next.js, React, TypeScript, Tailwind CSS, shadcn/ui

**Backend**
- Python, FastAPI, SQLAlchemy
- Celery or Temporal for background jobs

**AI / Orchestration**
- LLM providers: OpenAI / Gemini / Claude
- LangGraph — multi-agent orchestration
- LlamaIndex — data connectors and indexing
- Sentence Transformers (optional local embeddings)

**Database & Caching**
- PostgreSQL (+ pgvector for embeddings, stored alongside relational data)
- Redis — caching, queues

**Storage**
- S3-compatible object storage (MinIO for local dev, AWS S3 in production)

**Authentication**
- Clerk, Auth0, or Supabase Auth (app login)
- OAuth 2.0 per connector (Gmail, Slack, Google Drive, GitHub, etc.)

**Deployment / Infra**
- Docker, Kubernetes (optional, for scaling)
- GitHub Actions (CI/CD)
- App servers (Node.js/FastAPI), worker servers (Celery/Redis), search engine (OpenSearch), monitoring (Prometheus/Grafana), logging (ELK/Loki), message queue (RabbitMQ/Kafka)

---

## 13. Core AI Concepts Involved

1. **Data ingestion pipelines** — per-source connectors normalizing raw data (Slack, Gmail, PDFs, transcripts) into cleaned, chunked, embedded records.
2. **Embeddings** — convert text meaning into vectors so semantically related content can be found even without exact keyword matches.
3. **RAG (Retrieval-Augmented Generation)** — the core mechanism: retrieve relevant chunks from the workspace before generating an answer, so the LLM can answer using private data it wasn't trained on.
4. **Source attribution** — every stored chunk keeps metadata (source, date, author, url) so every generated answer can cite its evidence.

---

## 14. Development Roadmap

| Phase | Scope |
|---|---|
| **Phase 1 – Core MVP** | User auth, workspace creation, PDF/text uploads, chunking & embedding, semantic search with citations, chat interface (single user) |
| **Phase 2 – Connected Knowledge** | Gmail, Google Drive, Slack, Notion connectors; background/incremental sync |
| **Phase 3 – Collaboration** | Multiple workspaces, team members & roles, shared knowledge base, workspace-level permissions |
| **Phase 4 – AI Memory & Intelligence** | Daily briefing, meeting summaries, decision tracker, action-item extraction, opt-in personal memory, cross-source reasoning |
| **Phase 5 – Proactive AI Action Platform** | Email/Slack actions, workflow automation, approval flows, calendar scheduling, safe execution |
| **Phase 6 – Enterprise AI OS** | Multi-workspace + org RBAC & permissions, SSO & compliance, org memory & analytics, marketplace & APIs |

Guidance: **do not start with every connector at once (Slack + Gmail + Claude + Gemini + ChatGPT + Notes).** Ship Version 1 (PDFs, transcripts, notes, upload/ask/cite) first, then layer connectors incrementally.

---

## 15. Cost & Free-Tier Strategy

**Core principle: "free for users" is not "free for us."** The architecture must control AI spend from day one rather than assuming AI usage stays cheap at scale.

### 15.1 Where the cost actually comes from
| Component | Cost reality |
|---|---|
| LLM API calls (OpenAI/Anthropic/Gemini) | The dominant cost. Billed per-token, separate from any chat subscription. Scales directly with usage. |
| Agent loops | The hidden multiplier — a single "research and report" job can silently chain 6–8+ LLM calls (plan → search → analyze → search → analyze → summarize → write → verify). This, not connector count, is the real cost driver. |
| Google Calendar / Gmail APIs | Free within standard usage quotas today; Google has signaled quota/billing changes for scaled usage later in 2026 — design around quotas, don't assume permanently unlimited. |
| Telegram Bot API | Effectively free infrastructure-wise; the AI inference triggered by a Telegram message is what costs money, not the bot channel itself. |
| Other third-party connectors | Split into: free-within-quota (treat like Calendar/Gmail), paid/rate-limited (must be monitored), or requiring special/paid developer access (defer until there's revenue, or make optional). |

### 15.2 Cost-control architecture
```
USER
 │
 ↓
JOB
 │
 ↓
COST ESTIMATOR
 │
 ┌────────────┴────────────┐
 ↓                         ↓
SIMPLE JOB               COMPLEX JOB
 │                         │
CHEAPER MODEL           STRONGER MODEL
 │                         │
 └────────────┬────────────┘
              ↓
           RESULT
```
- Model routing by job complexity (this already matches the model routing / cost tracking called out in Section 12) rather than always invoking the strongest model.
- **Usage limits, not payment, at launch** — e.g. N jobs/month or N AI credits/month per free user, instead of unlimited usage. Don't launch 20 connectors + unlimited agents + unlimited research simultaneously; that combination is what produces a runaway bill.

### 15.3 Staged rollout (cost de-risking)
| Stage | Scope | Goal |
|---|---|---|
| **Stage 1 — Solo build** | You are the only user; local/small-API usage; 5–10 real jobs | Validate job creation, planner, tool system, connector OAuth, approval flow, background execution, job history, Telegram interface |
| **Stage 2 — Small beta (5–20 testers)** | Free tier, but capped jobs + capped AI credits | Measure actual cost-per-user with real usage patterns |
| **Stage 3 — Public free tier** | Free tier sized from Stage 2's measured cost-per-user | Offer a free tier you can sustain, not a guess |

The success bar for the earliest stage is qualitative, not scale: *"Can I make someone say: it actually completed the job?"* — cost optimization and monetization come after that's proven, not before.

---

## 16. Trust, Security & Privacy Requirements

- User owns their data at all times.
- End-to-end encryption.
- Source-level access control (per connector / per document).
- Audit logs & transparency for every AI action.
- Data residency options.
- SOC2 / GDPR readiness as a target for enterprise phase.
- Memory and actions are opt-in and require explicit user consent/confirmation.

---

## 17. Why This Project Has High Value (Portfolio/Business Framing)

Demonstrates, in one system:
- RAG pipelines
- Vector databases & hybrid/semantic search
- LLM application design
- Multi-source data ingestion pipelines
- Multi-agent AI system design
- Production-grade architecture (auth, permissions, sync, storage)
- Real business value or genuine product potential (not just a demo chatbot)

Positioning statement: *"Built an AI knowledge workspace that unifies documents, conversations, and meeting data using RAG pipelines, embeddings, vector search, and multi-agent LLM orchestration with source-grounded responses and safe, user-approved actions."*

---

## 18. Branding

**Name:** Sera — short, modern, timeless; calm, smart, future-ready; easy to pronounce and remember.

**Logomark:** Minimal, balanced mark of stacked rounded bars + a dot, representing:
- **Speed** (short top bar)
- **Structure** (stacked bars)
- **Focus** (the dot)
- **Flow** (the bottom bar)

Communicates: flow, structure, clarity, intelligent systems.

**Fit:** AI, SaaS, Tech, Data — works globally, scales across platforms (app icon, wordmark, dark/light variants, embossed/signage mockups all validated).

**Domain ideas:** sera.ai, sera.io, sera.app, getsera.com

---

## 19. Key Metrics to Track (Dashboard)

- Connected apps & per-source last-sync timestamp
- Documents indexed (count)
- Messages indexed (count)
- Embeddings generated (count)
- Query latency / answer confidence score
- Actions proposed vs. approved vs. executed vs. cancelled
- AI cost per user / per job (against free-tier quota, Section 15)
- Jobs created vs. completed, broken down by interface (Web, Telegram, future channels)
