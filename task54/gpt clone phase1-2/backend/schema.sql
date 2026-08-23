-- Module 4: Sidebar & Chat History — schema for folders, conversations, messages.
-- This mirrors backend/alembic/versions/0002_conversation_history.py exactly;
-- treat the Alembic migration as the source of truth for a real deployment
-- (it's what actually creates/versions the schema) — this file is the
-- plain-SQL reference the spec asked for, and is handy for a quick manual
-- `psql -f schema.sql` on a fresh database that already has migration 0001
-- (the `users` table) applied.

CREATE TYPE message_role AS ENUM ('user', 'assistant');

-- ---- folders --------------------------------------------------------------

CREATE TABLE folders (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(120) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_folders_user_id ON folders (user_id);

-- ---- conversations ----------------------------------------------------------

CREATE TABLE conversations (
    id                UUID PRIMARY KEY,
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    folder_id         UUID REFERENCES folders(id) ON DELETE SET NULL,
    title             VARCHAR(255) NOT NULL DEFAULT 'New chat',
    pinned            BOOLEAN NOT NULL DEFAULT false,
    archived          BOOLEAN NOT NULL DEFAULT false,
    -- NULL share_token = never shared. Revoking a share clears the token
    -- entirely (rather than a boolean flag) so a previously issued link can
    -- never be silently re-enabled by mistake.
    share_token       VARCHAR(43) UNIQUE,
    shared_at         TIMESTAMPTZ,
    -- Denormalized so the sidebar's recency sort never needs to join
    -- messages on every list request; kept in sync by the trigger below.
    last_message_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    search_vector     TSVECTOR,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_conversations_user_id ON conversations (user_id);
CREATE INDEX ix_conversations_user_last_message ON conversations (user_id, last_message_at);
CREATE INDEX ix_conversations_search_vector ON conversations USING gin (search_vector);

-- ---- messages -----------------------------------------------------------------

CREATE TABLE messages (
    id                UUID PRIMARY KEY,
    conversation_id   UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role              message_role NOT NULL,
    content           TEXT NOT NULL,
    search_vector     TSVECTOR,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);
CREATE INDEX ix_messages_search_vector ON messages USING gin (search_vector);

-- ---- full-text search: keep tsvector columns in sync automatically ------------
-- Titles and message content are indexed with the 'english' text search
-- config; switch to 'simple' if you need language-agnostic search instead.

CREATE FUNCTION conversations_search_vector_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_search_vector_update
    BEFORE INSERT OR UPDATE OF title ON conversations
    FOR EACH ROW EXECUTE FUNCTION conversations_search_vector_trigger();

CREATE FUNCTION messages_search_vector_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_search_vector_update
    BEFORE INSERT OR UPDATE OF content ON messages
    FOR EACH ROW EXECUTE FUNCTION messages_search_vector_trigger();

-- ---- keep conversations.last_message_at in sync on every new message ----------

CREATE FUNCTION conversations_touch_last_message_at() RETURNS trigger AS $$
BEGIN
    UPDATE conversations SET last_message_at = NEW.created_at WHERE id = NEW.conversation_id;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_touch_conversation
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION conversations_touch_last_message_at();

-- ---- example full-text search query (what GET /conversations/search runs) -----
-- Matches against both the conversation title and message content, ranks by
-- relevance, and returns a highlighted snippet from the best-matching message.
--
-- WITH q AS (SELECT plainto_tsquery('english', :search_term) AS query)
-- SELECT c.id, c.title, c.last_message_at,
--        GREATEST(ts_rank(c.search_vector, q.query),
--                 COALESCE(MAX(ts_rank(m.search_vector, q.query)), 0)) AS rank
-- FROM conversations c
-- CROSS JOIN q
-- LEFT JOIN messages m ON m.conversation_id = c.id AND m.search_vector @@ q.query
-- WHERE c.user_id = :user_id
--   AND (c.search_vector @@ q.query OR m.search_vector @@ q.query)
-- GROUP BY c.id, q.query
-- ORDER BY rank DESC, c.last_message_at DESC;
