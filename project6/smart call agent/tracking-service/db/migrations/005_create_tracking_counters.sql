-- One row per (prefix, year). The sequence for each is advanced with a
-- single atomic UPSERT (see src/generation/generateTrackingNumber.js) —
-- Postgres takes an internal row lock for INSERT ... ON CONFLICT DO UPDATE,
-- so concurrent bookings for the same prefix/year are serialized and never
-- hand out the same seq value or leave a gap.
CREATE TABLE IF NOT EXISTS tracking_counters (
    prefix      VARCHAR(4) NOT NULL,
    year        INTEGER NOT NULL,
    seq         INTEGER NOT NULL DEFAULT 0 CHECK (seq >= 0 AND seq <= 999999),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (prefix, year)
);
