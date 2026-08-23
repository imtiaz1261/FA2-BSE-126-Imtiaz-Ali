-- Bookable capacity per service, per location, per day, per time block.
CREATE TABLE IF NOT EXISTS slots (
    id            BIGSERIAL PRIMARY KEY,
    service_id    VARCHAR(64) NOT NULL,        -- references service-catalog.services.service_id
    location_id   VARCHAR(64) NOT NULL,        -- counter/branch id
    date          DATE NOT NULL,
    time_block    VARCHAR(11) NOT NULL,        -- e.g. '09:00-09:30'
    capacity      INTEGER NOT NULL CHECK (capacity >= 0),
    booked_count  INTEGER NOT NULL DEFAULT 0 CHECK (booked_count >= 0),
    held_count    INTEGER NOT NULL DEFAULT 0 CHECK (held_count >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- The core anti-double-booking guarantee at the schema level: only one
    -- row can ever exist for a given service/location/date/time_block.
    CONSTRAINT uq_slot UNIQUE (service_id, location_id, date, time_block),
    CONSTRAINT chk_capacity_not_exceeded CHECK (booked_count + held_count <= capacity)
);

CREATE INDEX IF NOT EXISTS idx_slots_lookup ON slots (service_id, location_id, date);
CREATE INDEX IF NOT EXISTS idx_slots_date ON slots (date);

-- Temporary reservations created by hold_slot(), promoted by confirm_slot()
-- or expired by the background sweeper job (jobs/expireHolds.js).
CREATE TABLE IF NOT EXISTS slot_holds (
    hold_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id       BIGINT NOT NULL REFERENCES slots(id),
    call_sid      VARCHAR(64) NOT NULL,
    status        VARCHAR(16) NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'confirmed', 'released', 'expired')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    confirmed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_holds_slot ON slot_holds (slot_id);
CREATE INDEX IF NOT EXISTS idx_holds_expiry ON slot_holds (status, expires_at)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_holds_call_sid ON slot_holds (call_sid);
