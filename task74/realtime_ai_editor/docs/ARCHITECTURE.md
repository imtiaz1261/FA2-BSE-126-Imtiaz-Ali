# Architecture

Browser:
React + TipTap
    |
    +-- Y.Doc (CRDT)
    |      |
    |      +-- y-websocket provider
    |
    +-- CollaborationCaret / awareness
    |
    +-- AI UI (/ai + autocomplete)
    |
    +-- version event API

Server:
Express
  /api/ai              -> OpenAI-compatible API
  /api/versions/:doc   -> demo version event store

WebSocket:
y-websocket
  -> broadcasts Yjs updates to clients in the same room

## Attribution

Human/AI distinction is tracked at the application event layer. A production implementation should attach immutable author metadata to Yjs transactions and persist update IDs/snapshots so attribution survives reconnects and server restarts.

## Version history

This demo records content snapshots after editor updates. A production implementation should store:
1. Yjs binary updates
2. periodic snapshots
3. actor/user ID
4. transaction ID
5. source = human | ai
6. timestamp
7. parent version

That enables exact time travel and auditability.
