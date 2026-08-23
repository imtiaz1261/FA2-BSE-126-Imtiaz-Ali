-- Service catalog: one row per bookable service type.
CREATE TABLE IF NOT EXISTS services (
    service_id          VARCHAR(64) PRIMARY KEY,
    name                 VARCHAR(128) NOT NULL,
    description          TEXT NOT NULL,
    required_documents   TEXT[] NOT NULL DEFAULT '{}',
    avg_duration_minutes INTEGER NOT NULL CHECK (avg_duration_minutes > 0),
    eligible_locations   TEXT[] NOT NULL DEFAULT '{}',
    -- Free-form synonyms/example phrases used to seed and sanity-check the
    -- LLM classifier prompt; not exhaustive, just anchoring examples.
    example_phrases      TEXT[] NOT NULL DEFAULT '{}',
    active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_services_active ON services (active);
