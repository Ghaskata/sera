# Sera build research notes — 2026-08-25

## Repository

The provided repository `Ghaskata/sera` is public, on `main`, and currently contains a Python FastAPI backend with PostgreSQL/pgvector, Google Drive OAuth/sync, Gemini embeddings/answers, APScheduler, and a Telegram bot. The latest commit is `8a2b611` from August 24, 2026.

## Google OAuth

Google’s official OAuth scope documentation states that OAuth scopes determine API access, sensitive scopes may require Google review, and public applications using user-data scopes may need verification. Sera should therefore request the narrowest read scopes needed for each connector, explain permissions clearly, and add Gmail/Calendar/Meet scopes incrementally rather than silently requesting every Google Workspace permission during first sign-in.

Official source: https://developers.google.com/identity/protocols/oauth2/scopes

## Product implication

The first implementation can safely establish a Google identity plus read-only Drive access, while connector contracts and staged OAuth flows prepare Gmail, Calendar, Meet, Maps, Keep/Notes, Slack, and Teams. Google sign-in alone must not be represented as authorization for non-Google services; each external provider needs its own consent or account-linking flow.
