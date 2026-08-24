# Slot Availability Engine — Module 5

Capacity calendar, real-time availability queries, and race-condition-safe
two-phase reservation (hold → confirm).

## 1. Schema

```sql
slots (
  id, service_id, location_id, date, time_block,   -- e.g. '09:00-09:30'
  capacity, booked_count, held_count,
  UNIQUE (service_id, location_id, date, time_block),
  CHECK (booked_count + held_count <= capacity)
)

slot_holds (
  hold_id UUID, slot_id, call_sid, status, created_at, expires_at, confirmed_at
)
```

Full DDL in `db/migrations/002_create_slots.sql`. The unique constraint on
`(service_id, location_id, date, time_block)` plus the `CHECK` constraint
are the schema-level backstop: it is structurally impossible to insert two
rows for the same slot, or to push `booked_count + held_count` past
`capacity`, no matter what application-level bugs exist above it.

## 2. Availability query logic (`GET /availability`)

```
GET /availability?service_id=&location_id=&preferred_date=&preferred_time=
```

1. **Exact match** — same service (+ location, if given), date, and
   `time_block`. If any matching row has `capacity - booked_count -
   held_count > 0`, return it immediately (`exactMatch: true`).
2. **Nearest alternatives** — if the exact block is full, search
   `preferred_date ± NEAREST_SEARCH_DAYS` (default 3), rank every available
   slot by `(day distance, time-of-day distance from the preferred block)`,
   and return the closest `NEAREST_RESULTS_LIMIT` (default 5). This is what
   lets the Voice Agent say "Tuesday at 10 is full, but I have Tuesday at
   11 or Wednesday at 9:30" instead of a flat "no availability."

Implemented in `src/availability/queryAvailability.js`.

## 3. Hold → confirm reservation (`src/reservation/reservationService.js`)

**`POST /hold`** — Phase 1, temporary reservation, expires after
`HOLD_TTL_SECONDS` (default 120s) if not confirmed. Two independent
concurrency layers, not one:

1. **Redis distributed lock** (`SET NX PX` + a Lua-scripted safe release in
   `src/db/distributedLock.js`) on the specific `service:location:date:
   time_block` key — fast rejection for a losing caller, avoids piling up
   DB connections under contention.
2. **Postgres `SELECT ... FOR UPDATE`** inside a transaction — the actual
   correctness guarantee. Even if the Redis lock were ever bypassed (e.g. a
   network partition to Redis from one app instance), the row lock plus the
   schema's `CHECK` constraint make double-booking structurally impossible,
   not just unlikely.

When capacity is down to its last remaining seat, two concurrent `hold`
requests for the same slot: one acquires the Redis lock and proceeds to the
row lock; the other either fails the Redis lock instantly (fast 409) or, in
the rare case both reach Postgres, blocks on `FOR UPDATE` until the first
transaction commits, then sees `remaining <= 0` and gets a clean `SLOT_FULL`
— never a phantom double-booking.

**`POST /confirm`** — Phase 2, promotes a hold to a confirmed booking
(`booked_count += 1`, `held_count -= 1`). Re-checks the hold is still
`active` and unexpired inside its own row-locked transaction; an
already-expired hold is refused and cleaned up on the spot rather than
silently confirmed.

**`POST /release`** — explicit early release (caller hangs up mid-call, or
rejects the readback and wants to renegotiate). The telephony gateway
(Module 2) and voice agent (Module 3) call this directly rather than
waiting for the TTL.

**Background sweeper** (`src/jobs/expireHolds.js`) — runs every
`HOLD_SWEEP_INTERVAL_MS` (default 15s), finds `active` holds past
`expires_at` using `FOR UPDATE SKIP LOCKED` (so it never blocks concurrent
hold/confirm traffic), and releases their capacity. This is the safety net
for holds that are never explicitly released — a crashed process, a missed
hangup event, etc.

## 4. Admin-configurable capacity (`src/capacity/capacityConfig.js`)

```
PUT /admin/capacity        { service_id, location_id, date, time_block, capacity }
PUT /admin/capacity/day    { service_id, location_id, date, capacity }   -- applies to every block that day
```

Used for cases like reduced capacity on a public holiday, or extended hours
for a high-demand day. Deliberately refuses to set `capacity` below the
current `booked_count` (`CAPACITY_BELOW_BOOKED`, HTTP 409) — an admin
cannot retroactively overbook a slot that already has confirmed
appointments.

## 5. Bootstrapping the calendar

```bash
npm run generate-slots -- id_card_renewal counter_1 30
```

Generates default business-hours blocks (`DEFAULT_DAY_START` →
`DEFAULT_DAY_END`, `DEFAULT_BLOCK_MINUTES` each) at
`DEFAULT_CAPACITY_PER_BLOCK` for the next N days, for one service/location.
Uses `ON CONFLICT DO NOTHING` so re-running it to extend the calendar
forward never overwrites admin capacity overrides already set on existing
dates. Run once per service/location combination from the catalog (Module
4), on a schedule (e.g. nightly, to keep rolling 60 days of calendar ahead).

## 6. On the database password

This module reads `DATABASE_URL` (including its password) from the
environment at runtime — see `.env.example`, which ships with a placeholder,
not a real credential. Nothing in this repo has a real database password
hardcoded in it, regardless of what password you're actually using, since
committing real secrets into source (even a private zip) makes them hard to
rotate and easy to leak later. Put your real value only in a local,
untracked `.env` file, e.g.:

```
DATABASE_URL=postgresql://slot_engine_user:YOUR_PASSWORD_HERE@localhost:5432/appointments
```

## 7. Environment variables

See `.env.example` for the full list and defaults.

## 8. Local development

```bash
npm install
cp .env.example .env   # then fill in your real DATABASE_URL
psql "$DATABASE_URL" -f db/migrations/002_create_slots.sql
npm run generate-slots -- id_card_renewal counter_1 30
npm run dev
```

## Next module

Module 6 (Appointment Booking & Confirmation Logic) is what calls
`POST /hold` and `POST /confirm` in sequence, orchestrated with the
Tracking-Number Generator and Receipt Service once the caller confirms.
