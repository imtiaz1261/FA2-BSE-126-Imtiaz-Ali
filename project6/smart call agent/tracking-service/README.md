# Tracking / Booking Number Generation — Module 7

A unique, human-speakable, typo-detecting reference for every confirmed
appointment.

## 1. Format

```
[SERVICE-PREFIX]-[YEAR]-[6-DIGIT SEQUENCE]-[CHECK-DIGIT]
IDR-2026-004821-7
```

- **SERVICE-PREFIX** — fixed 3-letter code per service, from an explicit
  maintained table (`src/generation/servicePrefixes.js`), not auto-derived
  from the service_id — auto-derivation risks collisions as the catalog
  (Module 4) grows (e.g. `passport_new` / `passport_renewal` both wanting
  "PN"/"PR"-ish codes). A human assigns a new prefix deliberately when a
  new service is added.
- **YEAR** — 4 digits, the year the appointment was booked.
- **SEQUENCE** — 6 digits, zero-padded, gap-free per (prefix, year).
- **CHECK-DIGIT** — 1 digit, a Luhn checksum over the whole payload
  including the prefix (see below).

## 2. Check-digit algorithm (`src/checksum/checkDigit.js`)

Luhn is defined over digits, but the payload includes letters. Letters are
folded to digits first — A=01 ... Z=26 — so `"IDR"` becomes
`"09" + "04" + "18" = "090418"`. The full numeric payload
(`foldedPrefix + year + sequence`) then goes through standard Luhn: double
every second digit counting from the rightmost payload digit (the check
digit itself is appended after and never doubled), subtract 9 from any
doubled digit over 9, sum everything, and
`checkDigit = (10 - (sum % 10)) % 10`.

This means a typo anywhere in the number — including the prefix letters,
not just the digits — changes the payload and gets caught by the check
digit.

## 3. Generation (`src/generation/generateTrackingNumber.js`)

Atomic, gap-free per (prefix, year):

```sql
INSERT INTO tracking_counters (prefix, year, seq)
VALUES ($1, $2, 1)
ON CONFLICT (prefix, year) DO UPDATE SET seq = tracking_counters.seq + 1
RETURNING seq;
```

This single statement is executed atomically by Postgres — it takes an
internal row lock for the duration of the upsert, so two concurrent
bookings for the same service in the same year are naturally serialized by
the database itself. Neither can observe or reuse the other's `seq` value,
and no application-level locking is needed.

`generateTrackingNumber()` optionally accepts an already-open `client` (a
pg transaction), so booking-service's atomic confirmation transaction
(Module 6) can call this as part of its own transaction — if that outer
transaction rolls back for any reason, this sequence increment rolls back
with it too. A failed or declined booking attempt never burns a sequence
number, which keeps gaps meaningful (a gap only ever means a real,
committed appointment existed and was later cancelled at the record level,
never a failed attempt).

## 4. Validation — fails fast, no database (`src/validation/validateTrackingNumber.js`)

```js
validateTrackingNumber("IDR-2026-004821-7")
// -> { valid: true, parsed: { prefix, year, sequence, checkDigit, normalized } }

validateTrackingNumber("IDR-2026-004821-3")
// -> { valid: false, reason: 'checksum_mismatch' }
```

Checks, in order: format via regex, prefix is a known service prefix, then
recomputes the check digit and compares. This is meant to run before any
database query — a status-check form or the dialogue manager's
status-check flow (Module 9) gets an instant, specific "that doesn't look
right" instead of a generic "not found" after a wasted DB round trip. Input
is normalized first (trimmed, uppercased, whitespace stripped, curly
hyphens straightened) so minor formatting differences in how someone reads
or types it back don't cause false rejections.

## 5. TTS read-back (`src/tts/formatForReadback.js`)

```js
formatForReadback("IDR-2026-004821-7")
// -> {
//      spokenText: "I, D, R -- two zero two six -- zero zero four, eight two one, seven",
//      displayGrouped: "IDR-2026-004-821-7"
//    }
```

- Prefix letters spelled out individually (TTS engines pronounce single
  capital letters as letter names reliably).
- Sequence + check digit (7 digits total) grouped into chunks of 3, each
  digit spoken as a full word, comma-separated between groups — easier to
  catch and write down over a phone line than one long run of digits.

The Voice Agent (Module 3) speaks `spokenText` slowly in
`FINAL_CONFIRMATION`, and the same tracking number is sent via SMS
immediately after (Module 10) using the plain `IDR-2026-004821-7` form.

## 6. API

```
POST /tracking/generate    { service_id, year? }        -> { trackingNumber }
GET  /tracking/validate    ?number=IDR-2026-004821-7     -> { valid, parsed? , reason? }
GET  /tracking/readback    ?number=IDR-2026-004821-7     -> { spokenText, displayGrouped }
```

## 7. Integration note

Module 6's booking-service originally shipped a lightweight standalone
tracking-number generator, explicitly flagged there as a placeholder ("to
be formalized in Module 7"). With this module built, booking-service should
call `generateTrackingNumber()` from here — ideally in-process by importing
this module's function and passing its own transaction `client` through
(both services share the same Postgres schema per Module 1's architecture),
so the sequence increment participates in the same atomic commit as the
appointment insert, exactly as described in section 3 above.

## 8. Environment variables

`DATABASE_URL` only — see `.env.example` (placeholder, no real credential
committed).

## 9. Local development

```bash
npm install
cp .env.example .env
psql "$DATABASE_URL" -f db/migrations/005_create_tracking_counters.sql
npm run dev
```

## Next module

Module 8 (Digital Receipt Generation) renders a printable/downloadable
receipt using the tracking number this module produces, formatted for
display (not spoken read-back) alongside the appointment details.
