# SERA Dashboard

A Vite + React + TypeScript starter for the SERA workspace dashboard. It includes connector cards, connection states, work-detective patterns, and a Memory Search surface for the Gemini RAG endpoint.

## Run locally

```bash
pnpm install
pnpm dev
```

Open `http://localhost:5173`. The Vite proxy expects the FastAPI backend at `http://127.0.0.1:8000` and forwards `/connectors`, `/rag`, and `/oauth` paths.

## Production build

```bash
pnpm build
pnpm preview
```

The dashboard currently uses realistic fallback catalog data if the backend is offline. Before production, connect the cards to a real browser-session authentication flow and replace the placeholder workspace ID in `src/App.tsx`; do not expose `RAG_QUERY_TOKEN` or provider credentials to client-side JavaScript.
