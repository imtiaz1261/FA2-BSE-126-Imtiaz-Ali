# Smart Appointment Call Agent

An AI-powered voice call system for citizen services (ID card renewal, new
ID card, passport appointments, child registration). The system handles
inbound phone calls end-to-end: understanding a caller's purpose, checking
real appointment availability, booking a slot, and issuing a tracking
number and a downloadable/printable receipt.

Built as a service-oriented monorepo — each module below is a standalone,
independently deployable Node.js/Express service sharing one PostgreSQL
database.

## Call flow, at a glance

```
Citizen dials -> Telephony Gateway -> Voice Agent (STT -> LLM dialogue -> TTS)
  -> purpose classified (Service Catalog) -> availability checked (Slot Engine)
  -> caller confirms day/time -> Booking Service commits atomically
  -> Tracking Service issues a number -> Receipt Service generates a PDF
  -> SMS/receipt sent to the caller
```

Full architecture diagrams, the call-sequence with error/fallback paths,
and the call-session state machine are in
[`phase1-system-architecture.md`](./phase1-system-architecture.md).

## Modules

| # | Module | Folder | What it does |
|---|---|---|---|
| 1 | System Architecture Overview | `phase1-system-architecture.md` | Component diagram, call sequence, state machine, repo layout |
| 2 | Telephony & Call Routing | `telephony-gateway/` | Answers calls, plays consent notice, bridges real-time audio, human-agent fallback, call queueing, recording |
| 3 | Conversational Voice Agent | `voice-agent/` | Streaming STT -> LLM dialogue manager -> TTS; slot-filling; barge-in; English/Urdu detection |
| 4 | Service Catalog & Purpose Classification | `service-catalog/` | Catalog data model + LLM classification of caller's purpose, with confidence-threshold clarification |
| 5 | Slot Availability Engine | `slot-engine/` | Capacity calendar, exact/nearest-alternative availability queries, hold-then-confirm reservation with Redis + row locking |
| 6 | Appointment Booking & Confirmation Logic | `booking-service/` | Atomic hold-to-appointment commit, caller-detail capture, readback confirmation, decline/renegotiate flow |
| 7 | Tracking / Booking Number Generation | `tracking-service/` | Unique checksummed tracking numbers, atomic gap-free sequencing, fast offline validation, TTS read-back formatting |
| 8 | Digital Receipt Generation | `receipt-service/` | Branded PDF receipt with QR check-in code, object storage, signed download URLs, phone-verified resend |

Modules 9–15 (Application Status Tracking, Notifications, Admin Dashboard,
Database & Backend Architecture, Security & Compliance, Deployment &
Scaling, Build Timeline) are not yet implemented.

## Repo structure

```
smart-appointment-agent/
├── phase1-system-architecture.md
├── telephony-gateway/
├── voice-agent/
├── service-catalog/
├── slot-engine/
├── booking-service/
├── tracking-service/
├── receipt-service/
└── (shared/, docs/ — see phase1-system-architecture.md for the full target layout)
```

Each service directory contains its own `src/`, `package.json`,
`.env.example`, `db/migrations/` (where applicable), and `README.md` with
implementation details specific to that module.

## Shared architectural decisions

- **Shared PostgreSQL, no private per-service database** — every service
  connects to the same Postgres instance/schema. This is what lets
  `booking-service` commit a capacity increment and an appointment insert
  in one atomic transaction, and lets `tracking-service`'s sequence
  generator participate in that same transaction.
- **Credentials never hardcoded** — every service ships an `.env.example`
  with placeholders only. Real values (database passwords, API keys, S3
  credentials) go in a local, untracked `.env`.
- **LLM does extraction and phrasing, never flow control** — the voice
  agent's dialogue state machine decides what's asked next; the LLM only
  extracts structured data and writes the natural-language reply for the
  current state.
- **Two independent layers guard against double-booking** — a Redis
  distributed lock (fast rejection) plus a Postgres `SELECT ... FOR UPDATE`
  row lock (the actual correctness guarantee) in the Slot Engine.
- **Side effects (SMS, receipt generation) happen after commit, never
  inside a database transaction** — a slow or failing external call must
  never roll back an otherwise-successful booking.

## Tech stack

Node.js/Express · PostgreSQL · Redis · Twilio (telephony) · LLM with
tool-calling (dialogue + classification) · streaming STT/TTS · PDFKit ·
S3-compatible object storage · English/Urdu bilingual support throughout.

## Getting started

Each service is run independently:

```bash
cd <service-name>
npm install
cp .env.example .env   # fill in real values locally
# apply that service's db/migrations/*.sql to your shared Postgres instance
npm run dev
```

Services are wired together via base-URL environment variables (e.g.
`SLOT_ENGINE_BASE_URL`, `BOOKING_SERVICE_BASE_URL`) — see each service's
`.env.example` for what it expects to reach.
