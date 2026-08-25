# Sera — Telegram-First Product Slice

**Status:** Implementation baseline
**Timebox:** One week

## Product direction

Sera is a real personal work-and-life assistant, not a hackathon-only dashboard. Telegram is the first user interface. A later web client will call the same backend services and job engine.

The product promise for this slice is: **Sera remembers the user’s connected work context, answers with evidence, and prepares safe next actions.**

## Week-one vertical slice

1. A user starts Sera in Telegram.
2. Sera creates a pending account and provides a secure Google sign-in link.
3. Google sign-in identifies the user and requests only the currently supported read permissions.
4. The callback links the Google identity to the Telegram identity and stores encrypted OAuth credentials.
5. Google Drive files are indexed into workspace-scoped chunks with source metadata.
6. Telegram questions are answered by Gemini using retrieved workspace context and source citations.
7. The connector and job abstractions are generalized so Gmail and Calendar can be added without rewriting account or query logic.
8. All external write actions remain disabled until an explicit approval flow is implemented.

## Connector boundaries

Google sign-in does not automatically authorize Slack, Microsoft Teams, or Telegram data. Those services require their own connector authorization or linking flows. The first implementation therefore treats Google identity and Google Drive as production-ready foundations, while Gmail, Calendar, Meet, Google Maps, Google Keep/Notes, Slack, and Teams are represented as provider-ready connector contracts and staged next steps.

## Safety requirements

OAuth state must be unpredictable and verified at callback time. OAuth tokens are encrypted at rest. Every query is scoped through the current user’s workspace. Gemini must not receive ungrounded private-data answers when retrieval returns no relevant context. No external message, email, calendar change, or other write action is executed without an explicit approval record.

## Success criteria

The slice is complete when a configured deployment can run Telegram polling, complete Google sign-in from Telegram, persist a linked account, index Drive content, answer a cited question through Gemini, and pass automated tests for state validation, workspace isolation, token encryption, and citation behavior.

## Deferred work

The next slices add Gmail, Calendar, Meet transcript ingestion, general connector capability metadata, durable background workers, personal memory extraction, repetitive-work detection, generated workflow plans, and approval-backed execution. Slack and Teams require separate OAuth applications and permissions; they are not silently implied by Google login.
