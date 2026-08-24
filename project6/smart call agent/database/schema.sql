CREATE TABLE IF NOT EXISTS services (
    service_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    required_documents TEXT,
    avg_duration_minutes INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    address TEXT NOT NULL,
    contact_number VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS slots (
    slot_id BIGSERIAL PRIMARY KEY,
    service_id VARCHAR(64) NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    location_id VARCHAR(64) NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
    slot_date DATE NOT NULL,
    time_block VARCHAR(20) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    booked_count INTEGER NOT NULL DEFAULT 0 CHECK (booked_count >= 0),
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (service_id, location_id, slot_date, time_block)
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id BIGSERIAL PRIMARY KEY,
    tracking_number VARCHAR(32) NOT NULL UNIQUE,
    service_id VARCHAR(64) NOT NULL REFERENCES services(service_id) ON DELETE RESTRICT,
    location_id VARCHAR(64) NOT NULL REFERENCES locations(location_id) ON DELETE RESTRICT,
    slot_id BIGINT REFERENCES slots(slot_id) ON DELETE RESTRICT,
    applicant_name VARCHAR(150) NOT NULL,
    phone_number VARCHAR(32) NOT NULL,
    cnic_number VARCHAR(32),
    status VARCHAR(64) NOT NULL DEFAULT 'Booked',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('Booked', 'CheckedIn', 'DocumentsVerified', 'Processing', 'ReadyForCollection', 'Completed'))
);

CREATE TABLE IF NOT EXISTS status_history (
    status_history_id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES appointments(appointment_id) ON DELETE CASCADE,
    status VARCHAR(64) NOT NULL,
    changed_by VARCHAR(64),
    note TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_logs (
    call_id BIGSERIAL PRIMARY KEY,
    phone_number VARCHAR(32) NOT NULL,
    transcript TEXT,
    outcome VARCHAR(64) NOT NULL,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications_log (
    notification_id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT REFERENCES appointments(appointment_id) ON DELETE SET NULL,
    channel VARCHAR(32) NOT NULL CHECK (channel IN ('sms', 'email', 'voice', 'receipt')),
    template_name VARCHAR(120) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    payload JSONB,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staff_users (
    staff_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('counter_staff', 'admin')),
    location_id VARCHAR(64) REFERENCES locations(location_id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_tracking_number ON appointments(tracking_number);
CREATE INDEX IF NOT EXISTS idx_appointments_phone_number ON appointments(phone_number);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_service_location ON appointments(service_id, location_id, status);
CREATE INDEX IF NOT EXISTS idx_slots_service_date_time ON slots(service_id, location_id, slot_date, time_block);
CREATE INDEX IF NOT EXISTS idx_status_history_appointment ON status_history(appointment_id, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_logs_phone_created ON call_logs(phone_number, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_appointment ON notifications_log(appointment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_staff_users_email ON staff_users(email);

CREATE OR REPLACE FUNCTION prevent_overbooking()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.booked_count > (SELECT capacity FROM slots WHERE slot_id = NEW.slot_id) THEN
        RAISE EXCEPTION 'Booked count exceeds slot capacity';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_overbooking
BEFORE INSERT OR UPDATE ON slots
FOR EACH ROW
EXECUTE FUNCTION prevent_overbooking();

ALTER TABLE appointments
ADD CONSTRAINT appointments_single_active_status
CHECK (status <> '');
