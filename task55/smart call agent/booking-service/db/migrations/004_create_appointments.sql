-- Permanent appointment record. Created only inside the atomic confirmation
-- transaction (src/confirmation/confirmAppointment.js) — never inserted on
-- its own, since an appointment without a corresponding booked_count
-- increment on its slot would mean a phantom booking.
CREATE TABLE IF NOT EXISTS appointments (
    id              BIGSERIAL PRIMARY KEY,
    tracking_number VARCHAR(32) NOT NULL UNIQUE,

    service_id      VARCHAR(64) NOT NULL,
    location_id     VARCHAR(64) NOT NULL,
    date            DATE NOT NULL,
    time_block      VARCHAR(11) NOT NULL,

    slot_id         BIGINT NOT NULL REFERENCES slots(id),
    hold_id         UUID NOT NULL REFERENCES slot_holds(hold_id),

    caller_name     VARCHAR(128) NOT NULL,
    cnic            VARCHAR(15),              -- nullable, format 12345-1234567-1
    phone_number    VARCHAR(20) NOT NULL,
    call_sid        VARCHAR(64),

    status          VARCHAR(16) NOT NULL DEFAULT 'confirmed'
                    CHECK (status IN ('confirmed', 'completed', 'cancelled', 'no_show')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A hold can only ever produce one appointment.
    CONSTRAINT uq_appointment_hold UNIQUE (hold_id)
);

CREATE INDEX IF NOT EXISTS idx_appointments_tracking ON appointments (tracking_number);
CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments (phone_number);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments (date);
