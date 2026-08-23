# Application Status Tracking — Module 9

Lets citizens check application progress after booking, via the same phone
call, SMS keyword, or a self-service web page — and lets staff move the
status forward as the application physically progresses.

## 1. Status data model

```
Booked -> CheckedIn -> DocumentsVerified -> Processing -> ReadyForCollection -> Completed
Cancelled (reachable from any non-terminal state)
```

`appointments.status` (Module 6's table, expanded here — see
`db/migrations/008_add_status_tracking.sql`) now uses this full enum
instead of the booking-time-only `confirmed/completed/cancelled/no_show`
set; existing rows are migrated forward (`confirmed` -> `Booked`, etc.).

```sql
status_history (
  id, tracking_number REFERENCES appointments,
  from_status, to_status, staff_id NULLABLE, note NULLABLE, changed_at
)
```

Append-only audit trail — every transition, who made it (NULL for
system-driven ones like the initial booking), and when. The migration also
backfills an initial "Booked" row for every appointment that predates it.

Transition rules (`src/status/statusModel.js`): forward-only along the
progression order (skipping stages is allowed — real counter workflows
don't always hit every intermediate step — but moving backward is
rejected), `Cancelled` reachable from any non-terminal state, nothing
transitions out of a terminal state (`Completed`/`Cancelled`).

## 2. Status lookup — privacy-safe (`GET /status/:trackingNumber`)

```
GET /status/IDR-2026-004821-7?phone=+923001234567
```

Requires both the tracking number and the phone number on file to match
(last-10-digits comparison, tolerant of formatting) before returning
anything — knowing a tracking number alone isn't sufficient to see someone
else's application status. Returns current status plus the full
`status_history`.

## 3. Staff update (`PUT /status/:trackingNumber`)

```json
PUT /status/IDR-2026-004821-7
{ "to_status": "DocumentsVerified", "staff_id": "staff_042", "note": "CNIC + photo verified" }
```

This is the hook Module 11 (Admin/Staff Console) calls. Atomic: updates
`appointments.status` and appends the `status_history` row in one
transaction (`src/status/updateStatus.js`), so the two can never disagree.
Rejects invalid/backward transitions with `409 invalid_transition`.

## 4. Voice status-check flow

Not a new telephony endpoint — this extends the Voice Agent's (Module 3)
dialogue manager with a second intent alongside booking:

1. Caller says "check my application status" (or similar) instead of
   stating a purpose of visit.
2. Caller provides their tracking number — spoken (extracted the same way
   `record_turn` extracts other slots) or via DTMF keypad entry, which the
   telephony gateway (Module 2) forwards as digits.
3. The dialogue manager calls `GET /status/:trackingNumber?phone=<caller's
   caller-ID number, already in the call session>` — no extra verification
   question needed, since the phone is already known from Module 2.
4. The dialogue manager speaks `buildStatusReadback()`'s output
   (`src/voice/statusReadback.js`) — bilingual, template-based status
   descriptions for the same reason the booking readback is templated:
   status must never be paraphrased loosely.

## 5. SMS-keyword flow (`POST /sms/inbound`)

Twilio inbound-SMS webhook. A citizen texts their tracking number (e.g.
`"IDR-2026-004821-7"` or `"status IDR-2026-004821-7"`) to the service
number:

1. `extractAndValidateTrackingNumber()` pulls the tracking-number-shaped
   substring out of the free-form text and validates it via
   tracking-service's `/tracking/validate` (Module 7) — format +
   checksum, no database hit — before ever looking anything up.
2. Privacy verification uses the SMS sender's own phone number (Twilio's
   `From`) as the phone to check against the appointment on file — texting
   in from the same number used to book is itself the verification, no
   extra step required from the citizen.
3. Replies via `MessagingResponse` TwiML with the current status in plain
   English (SMS keeps to one language for simplicity/cost; the voice flow
   above is where bilingual support lives).

## 6. Proactive milestone SMS

`src/notifications/notifyClient.js` fires only on `ReadyForCollection` and
`Completed` (`NOTIFY_ON_STATUSES` in `statusModel.js`) — not on every
intermediate stage, since pushing a notification for every internal step
(`CheckedIn`, `DocumentsVerified`, `Processing`) would train citizens to
start ignoring the SMS channel. Triggered from `updateStatus()` after the
transition commits, same pattern as every other notification trigger in
this project — a failed SMS send never undoes a real status change.

## 7. API

```
GET  /status/:trackingNumber   ?phone=...                     -> { trackingNumber, currentStatus, history }
PUT  /status/:trackingNumber   { to_status, staff_id, note? }  -> { trackingNumber, fromStatus, toStatus }
POST /sms/inbound              (Twilio webhook: From, Body)    -> TwiML <Message>
```

## 8. On credentials

`.env.example` ships with placeholders only. Fill in real values in a
local, untracked `.env`.

## 9. Local development

```bash
npm install
cp .env.example .env
psql "$DATABASE_URL" -f db/migrations/008_add_status_tracking.sql
npm run dev
```

Requires `appointments` (Module 6) already migrated in the same database —
this migration ALTERs that table.

## Next module

Module 10 (Notifications) is what actually delivers the SMS this module
triggers (`/notify/status-milestone`) — currently a placeholder endpoint
this and other modules call but that doesn't exist yet. Module 11
(Admin/Staff Console) is the UI that calls `PUT /status/:trackingNumber` as
staff process applications.
