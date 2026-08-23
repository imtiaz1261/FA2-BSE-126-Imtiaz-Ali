-- Expands appointments.status (Module 6 only needed
-- confirmed/completed/cancelled/no_show at booking time) to the full
-- post-booking lifecycle, and adds a full audit trail of every transition.

ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_status_check;

-- Migrate Module 6's booking-time values onto the new enum before adding
-- the new constraint, so existing rows stay valid.
UPDATE appointments SET status = 'Booked' WHERE status = 'confirmed';
UPDATE appointments SET status = 'Completed' WHERE status = 'completed';
UPDATE appointments SET status = 'Cancelled' WHERE status = 'cancelled';
UPDATE appointments SET status = 'Cancelled' WHERE status = 'no_show';

ALTER TABLE appointments ALTER COLUMN status SET DEFAULT 'Booked';
ALTER TABLE appointments ADD CONSTRAINT appointments_status_check
    CHECK (status IN (
        'Booked', 'CheckedIn', 'DocumentsVerified', 'Processing',
        'ReadyForCollection', 'Completed', 'Cancelled'
    ));

-- Full audit trail: every transition, who made it (if a staff action), and
-- when. Never updated or deleted, only appended to.
CREATE TABLE IF NOT EXISTS status_history (
    id              BIGSERIAL PRIMARY KEY,
    tracking_number VARCHAR(32) NOT NULL REFERENCES appointments(tracking_number),
    from_status     VARCHAR(24),                  -- NULL for the initial "Booked" row
    to_status       VARCHAR(24) NOT NULL,
    staff_id        VARCHAR(64),                   -- NULL for system-driven transitions (e.g. initial booking)
    note            TEXT,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_status_history_tracking ON status_history (tracking_number, changed_at);

-- Seed the initial "Booked" history row for any appointment that doesn't
-- have one yet (i.e. everything booked before this migration ran).
INSERT INTO status_history (tracking_number, from_status, to_status, staff_id, changed_at)
SELECT tracking_number, NULL, 'Booked', NULL, created_at
FROM appointments a
WHERE NOT EXISTS (
    SELECT 1 FROM status_history h WHERE h.tracking_number = a.tracking_number
);
