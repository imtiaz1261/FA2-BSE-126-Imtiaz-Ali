# Appointment Booking & Confirmation Logic — Module 6

Turns a held slot (Module 5) plus captured caller details into a permanent,
trackable appointment — atomically.

## 1. Appointment data model

```sql
appointments (
  id, tracking_number UNIQUE,
  service_id, location_id, date, time_block,
  slot_id REFERENCES slots(id),
  hold_id REFERENCES slot_holds(hold_id) UNIQUE,   -- one hold -> at most one appointment
  caller_name, cnic NULLABLE, phone_number, call_sid,
  status DEFAULT 'confirmed' CHECK (status IN ('confirmed','completed','cancelled','no_show')),
  created_at, updated_at
)
```

Full DDL in `db/migrations/004_create_appointments.sql`. `hold_id` is
`UNIQUE` so a hold can never be confirmed twice into two appointment rows,
even under a retried request.

## 2. Caller-detail capture (`src/confirmation/captureCallerDetails.js`)

- **Name** — required, minimum 2 characters after trimming.
- **CNIC** — optional (per the design brief, "if available"); if given,
  validated/normalized against `12345-1234567-1`. Absence is never an
  error; a malformed value is.
- **Phone** — required, but defaults to `phone_from_caller_id` (the Twilio
  `From` number already captured by the telephony gateway in Module 2) if
  the caller doesn't explicitly give or correct one. Validated as
  10-15 digits, optional leading `+`.

Validation happens before the confirmation transaction opens — a bad phone
number fails fast with a 400, never inside a held database lock.

## 3. The atomic confirmation transaction (`src/confirmation/confirmAppointment.js`)

Single Postgres transaction, in order:

1. `SELECT ... FOR UPDATE OF h, s` locks both the `slot_holds` row and its
   parent `slots` row together.
2. Verify the hold is `active` and unexpired — an expired-but-unswept hold
   is cleaned up and the confirm is refused, never silently honored.
3. Promote the hold: `status = 'confirmed'`.
4. `booked_count += 1`, `held_count -= 1` on the slot — protected by
   `slots.chk_capacity_not_exceeded` from Module 5 as a last-resort
   guarantee.
5. Generate a tracking number and insert the `appointments` row, retrying
   up to `TRACKING_NUMBER_MAX_RETRIES` times on the rare unique-constraint
   collision (`23505`) without failing the whole booking.
6. `COMMIT`. Any failure at any step -> `ROLLBACK`, and nothing — not the
   hold promotion, not the capacity increment, not the appointment row — is
   left partially applied.

**SMS is triggered after commit, not inside the transaction**
(`src/notifications/notifyClient.js`) — a slow or failing SMS provider must
never hold a database transaction open or cause a successful booking to
roll back. Notification failures are logged, not thrown; the appointment is
already real regardless.

### Why this touches the slots/slot_holds tables directly instead of calling Slot Engine's API

The design brief requires true atomicity across the capacity increment and
the appointment insert. Per Module 1's architecture ("no private database —
all persistent state lives in the shared PostgreSQL instance"),
booking-service and slot-engine share the same Postgres schema, so this one
transaction can safely touch both. `POST /hold` and the decline-path
`POST /release` still go through Slot Engine's own HTTP API, since those
are reversible, non-critical operations already protected by the 2-minute
hold TTL — only the irreversible commit path needs the stronger,
single-transaction guarantee.

## 4. Readback before confirming (`src/dialogue/confirmationReadback.js`)

Template-based (not LLM-generated) bilingual readback text — this is the
one sentence in the call that must never be paraphrased loosely:

- EN: "Let me confirm — that's ID Card Renewal on 2026-08-15 at
  10:00-10:30, at Counter 2. Should I go ahead and book that?"
- UR: "Tasdeeq kar lete hain — ID Card Renewal ke liye 2026-08-15 ko
  10:00-10:30 baje, Counter 2 mein. Kya main yeh book kar doon?"

The Voice Agent's dialogue manager (Module 3) speaks this in
`CONFIRMING_DATETIME`, and only calls `POST /appointments/confirm` on an
explicit "yes"/"confirm" classification from that turn — never on silence,
a vague murmur, or inferred tone.

## 5. Decline flow (`src/confirmation/declineSlot.js`)

On "no": releases the hold via Slot Engine's `POST /release` immediately
(freeing capacity for other callers right away rather than waiting out the
TTL), then re-queries `GET /availability` for the next best options in the
same call — so the dialogue manager can offer an alternative without a dead
end, looping back into `CAPTURING_DAY`/`CAPTURING_TIME`.

## 6. API

```
POST /appointments/confirm    { hold_id, call_sid, name, cnic?, phone?, phone_from_caller_id }
                               -> { trackingNumber, serviceId, locationId, date, timeBlock, status }

POST /appointments/decline    { hold_id, service_id, location_id?, preferred_date, preferred_time }
                               -> { exactMatch, slots, alternatives }   (Module 5's availability shape)

GET  /appointments/:trackingNumber  -> full appointment record
```

## 7. On credentials

`.env.example` ships with placeholders only — no real database password is
committed here. Put your actual value in a local, untracked `.env`:

```
DATABASE_URL=postgresql://booking_service_user:YOUR_PASSWORD_HERE@localhost:5432/appointments
```

## 8. Local development

```bash
npm install
cp .env.example .env
psql "$DATABASE_URL" -f db/migrations/004_create_appointments.sql
npm run dev
```

Requires slot-engine's migrations (`slots`, `slot_holds`) already applied
to the same database, since `appointments.slot_id`/`hold_id` reference them.

## Next module

Module 7 (Tracking / Booking Number Generation) formalizes the tracking
number scheme beyond this module's lightweight generator (service-specific
prefixing rules, checksum digit, etc.), and Module 8 (Digital Receipt
Generation) reads the `appointments` row this module produces to render a
printable receipt.
