# Realtime AI Collaborative Editor

A minimal Notion-style collaborative document editor built with:
- React + Vite
- TipTap
- Yjs CRDT
- y-websocket
- Express
- OpenAI-compatible AI endpoint
- SQLite-style JSON persistence for version history (demo implementation)

## Features
- Real-time collaborative editing through Yjs + WebSocket
- Multiple users can edit the same document
- User cursors/presence
- `/ai` command menu for rewrite, summarize, continue
- Inline grey autocomplete suggestion; press Tab to accept
- Version history
- Human vs AI edit attribution in the UI
- AI operations are represented separately from human edits

## Run

Requirements: Node.js 20+

```bash
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 in two browser tabs to test collaboration.

For AI features, set:
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-20b

The included server uses the OpenAI-compatible SDK configured for Groq. If no API key is configured, AI calls return a helpful demo response instead of failing.

## Production notes

This is a runnable starter, not a production SaaS. For production:
- authenticate users and documents
- persist Yjs updates in Postgres/object storage
- use Redis/pubsub when scaling WebSocket nodes
- store immutable version snapshots/deltas
- authorize document access server-side
- add rate limits and audit logging
- never expose the API key to the browser
