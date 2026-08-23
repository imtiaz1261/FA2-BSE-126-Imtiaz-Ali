# Module 4: Sidebar & Chat History — what to do with this

New and changed files only — copy each into your project at the matching
path, overwriting what's there.

## Copy these in

**Backend:**
- `backend/app/models.py` — adds `Folder`, `Conversation`, `Message` models
- `backend/app/schemas_conversations.py` — new file
- `backend/app/schemas_chat.py` — `ChatMessage` now carries a client-generated `id`
- `backend/app/routers/conversations.py` — new file (conversations + folders CRUD, search)
- `backend/app/routers/share.py` — new file (public read-only share endpoint)
- `backend/app/routers/chat.py` — now persists every turn and returns `conversation_id`
- `backend/app/main.py` — wires up the two new routers
- `backend/alembic/versions/0002_conversation_history.py` — the real migration
- `backend/schema.sql` — plain-SQL reference (the migration is the source of truth; this is for reading/manual `psql -f` use)

**Frontend:**
- `frontend/src/features/sidebar/**` — 6 components + the row-grouping helper
- `frontend/src/hooks/useElementSize.ts`, `useDebouncedValue.ts` — new
- `frontend/src/store/conversationsStore.ts` — new
- `frontend/src/store/chatStore.ts` — now tracks `conversationId`, loads/starts conversations, and refreshes the sidebar after each turn
- `frontend/src/lib/conversationsApi.ts` — new
- `frontend/src/lib/api.ts` — one-line fix (see below)
- `frontend/src/features/chat/lib/chatStream.ts` — now sends/receives `conversation_id`
- `frontend/src/App.tsx` — renders the sidebar, and a public `/share/:token` route
- `frontend/package.json` — adds `react-window`

Then, from `frontend/`:
```powershell
npm install
```

Run the migration:
```powershell
alembic upgrade head
```

## What's implemented

**Backend — `/conversations`, `/folders`, `/share`:**
- `GET /conversations` — keyset-paginated (cursor on `last_message_at, id`), pinned items always returned in full on page one, `date_group` (`today`/`yesterday`/`previous_7_days`/`older`) computed server-side per item.
- `POST /conversations`, `PATCH /conversations/{id}` (rename/pin/archive/move folders), `DELETE /conversations/{id}`.
- `GET /conversations/search?q=` — Postgres full-text search across **both** conversation titles and message content, ranked with `ts_rank`, with a `ts_headline` snippet showing where the match was found.
- `POST /conversations/{id}/share` / `DELETE .../share` — idempotent share-link creation, explicit revocation (clears the token rather than a boolean flag, so a revoked link can never be silently re-enabled).
- `GET /share/{token}` — public, unauthenticated, rate-limited, and returns a **deliberately separate, narrower schema** (`SharedConversationResponse`) so no internal field can ever leak through by accident.
- Full-text search is powered by **generated `tsvector` columns kept in sync by DB triggers** — insert or edit a title/message and the index updates itself; application code never has to remember to re-index.
- `conversations.last_message_at` is denormalized and kept in sync by a trigger on message insert, so the sidebar's recency sort never joins `messages` at read time.
- Chat persistence uses a "full history replace" strategy per turn — documented in `chat.py`'s module docstring — which trades a little extra write volume for not needing a client/server diff algorithm to agree.

**Frontend:**
- `Sidebar` — collapsible, "New chat" pinned at top, folder filter chips, grouped list (Pinned, Today, Yesterday, Previous 7 Days, Older), virtualized with `react-window`'s `VariableSizeList` (handles 1000+ conversations smoothly — headers and rows have different heights, hence *Variable*Size), infinite-scroll pagination that fetches the next page ~10 rows before the end.
- `SidebarSearchBox` — 300ms debounced, filters in place; out-of-order slow responses are discarded so a fast later query can't get overwritten by a stale earlier one.
- `ConversationRow` — hover-to-reveal action menu (rename inline, pin, share, archive, delete), all with optimistic local updates and rollback on failure.
- `ShareDialog` — create/copy/revoke a read-only link.
- `SharedConversationView` — the public `/share/:token` page, no auth, no sidebar.

## Bugs found and fixed while assembling this

1. **`apiRequest`'s method union didn't include `"PATCH"`.** `conversationsApi.patch()` (rename/pin/archive/move) would have failed to type-check. One-line fix in `lib/api.ts`.
2. **`ShareDialog` didn't update local state after sharing/revoking.** The sidebar item's `is_shared` flag only ever came from the last list/search fetch, so reopening the dialog for a just-shared conversation would show "Create link" instead of the existing one until the next refetch. Added a `setShared` action to `conversationsStore` and wired it in.

## Try it

```powershell
uvicorn app.main:app --reload   # backend
npm run dev                      # frontend
```

Send a few messages to create conversations, then check: pin one, rename one,
search for a word that only appears in a message body (not the title) to see
full-text search working, share one and open the link in a private window,
and scroll the sidebar to see virtualization + pagination kick in once you
have enough history.
