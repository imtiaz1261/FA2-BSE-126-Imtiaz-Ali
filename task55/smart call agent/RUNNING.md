# Running the Smart Appointment Call Agent locally

Complete command sequence to bring up every service built so far
(Modules 1-8). Run each numbered step in order.

## 0. Prerequisites

- Node.js 18+ and npm
- Docker + Docker Compose (for Postgres/Redis/MinIO — or point at your own
  instances instead, see step 1)
- `psql` CLI (for running migrations)
- Real API keys for: Twilio, your STT/TTS provider, Anthropic — only
  needed to actually place/receive live phone calls (Modules 2 & 3). Every
  other module can be started and smoke-tested with `curl` without them —
  see step 7.

## 1. Start infrastructure (Postgres, Redis, MinIO)

From the project root:

```bash
docker compose up -d
```

This starts:
- Postgres on `localhost:5432` (db `appointments`, user `appuser`, password `changeme_locally` unless you override `POSTGRES_PASSWORD`)
- Redis on `localhost:6379`
- MinIO (S3-compatible storage) on `localhost:9100` (API) / `localhost:9101` (console), user `minioadmin` / `minioadmin123` unless overridden

Wait for them to report healthy:

```bash
docker compose ps
```

Create the MinIO bucket receipt-service will upload to:

```bash
docker run --rm --network host minio/mc \
  alias set local http://localhost:9100 minioadmin minioadmin123
docker run --rm --network host minio/mc mb local/citizen-services-receipts
```

## 2. Apply database migrations

```bash
export DATABASE_URL=postgresql://appuser:changeme_locally@localhost:5432/appointments
chmod +x scripts/run-migrations.sh
./scripts/run-migrations.sh
```

This runs, in the required dependency order: `service-catalog` ->
`slot-engine` -> `tracking-service` -> `booking-service` ->
`receipt-service` -> `status-service` (each later one references or alters
tables created by an earlier one — `status-service`'s migration in
particular `ALTER`s the `appointments` table from `booking-service`).

## 3. Install dependencies for every service

```bash
for svc in telephony-gateway voice-agent service-catalog slot-engine booking-service tracking-service receipt-service status-service; do
  (cd "$svc" && npm install)
done
```

## 4. Configure each service's .env

For each service, copy the template and fill in real values:

```bash
for svc in telephony-gateway voice-agent service-catalog slot-engine booking-service tracking-service receipt-service status-service; do
  cp "$svc/.env.example" "$svc/.env"
done
```

Then edit each `.env`. Minimum required per service:

| Service | Must set for basic local testing | Also needs (for live calls) |
|---|---|---|
| `service-catalog` | `DATABASE_URL`, `ANTHROPIC_API_KEY` | — |
| `slot-engine` | `DATABASE_URL`, `REDIS_URL` | — |
| `booking-service` | `DATABASE_URL`, `SLOT_ENGINE_BASE_URL=http://localhost:6000`, `NOTIFICATION_SERVICE_BASE_URL=http://localhost:8000` (placeholder, see note below) | — |
| `tracking-service` | `DATABASE_URL` | — |
| `receipt-service` | `DATABASE_URL`, `S3_ENDPOINT=http://localhost:9100`, `S3_ACCESS_KEY_ID=minioadmin`, `S3_SECRET_ACCESS_KEY=minioadmin123`, `BOOKING_SERVICE_BASE_URL=http://localhost:7000`, `SERVICE_CATALOG_BASE_URL=http://localhost:5000`, `NOTIFICATION_SERVICE_BASE_URL=http://localhost:8000` (placeholder) | — |
| `telephony-gateway` | `MEDIA_STREAM_WSS_URL`, `VOICE_AGENT_WS_URL=ws://localhost:4000/session`, `PUBLIC_BASE_URL` (your ngrok URL, or any placeholder for local-only testing) | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SERVICE_NUMBER` |
| `voice-agent` | `SLOT_ENGINE_BASE_URL=http://localhost:6000`, `BOOKING_SERVICE_BASE_URL=http://localhost:7000` | `STT_API_KEY`, `TTS_API_KEY`, `ANTHROPIC_API_KEY` |
| `status-service` | `DATABASE_URL`, `BOOKING_SERVICE_BASE_URL=http://localhost:7000`, `TRACKING_SERVICE_BASE_URL=http://localhost:8500`, `NOTIFICATION_SERVICE_BASE_URL=http://localhost:8000` (placeholder) | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (only for the inbound-SMS webhook) |

> Note on `NOTIFICATION_SERVICE_BASE_URL`: Module 10 (Notifications) hasn't
> been built yet, but `booking-service` and `receipt-service` still require
> this variable to be set to start (even though the endpoint doesn't exist
> yet). Point it at any placeholder URL, e.g. `http://localhost:8000` — the
> actual notification-trigger calls are wrapped in try/catch and only log
> an error; they won't crash the service or block a booking/receipt from
> completing.

> Note on Twilio/STT/TTS/Anthropic keys: without these, `telephony-gateway`
> and `voice-agent` will still start, but you can't place a real phone call
> or run a live dialogue turn. Every other service (service-catalog,
> slot-engine, booking-service, tracking-service, receipt-service) is fully
> testable via `curl` without any of these keys except `ANTHROPIC_API_KEY`
> for service-catalog's `/classify` endpoint.

## 5. Bootstrap the slot calendar

service-catalog auto-seeds its 5 default services on first boot (next
step). After slot-engine is running (step 6), generate 30 days of slots
for each service/location combination you want bookable:

```bash
cd slot-engine
npm run generate-slots -- id_card_renewal counter_1 30
npm run generate-slots -- new_id_card counter_1 30
npm run generate-slots -- passport_new counter_3 30
npm run generate-slots -- passport_renewal counter_3 30
npm run generate-slots -- child_registration counter_5 30
cd ..
```

## 6. Start every service

Open a separate terminal per service (or use a process manager like `pm2`
or `concurrently`):

```bash
cd service-catalog   && npm run dev   # :5000
cd slot-engine        && npm run dev   # :6000
cd booking-service    && npm run dev   # :7000
cd tracking-service   && npm run dev   # :8500
cd receipt-service    && npm run dev   # :9000
cd status-service      && npm run dev   # :9500
cd voice-agent          && npm run dev   # :4000
cd telephony-gateway    && npm run dev   # :3000
```

Or launch them all in the background from one terminal:

```bash
for svc in service-catalog:5000 slot-engine:6000 booking-service:7000 \
           tracking-service:8500 receipt-service:9000 status-service:9500 \
           voice-agent:4000 telephony-gateway:3000; do
  name="${svc%%:*}"
  (cd "$name" && npm run dev > "../logs-$name.log" 2>&1 &)
done
```

Check they're all up:

```bash
for port in 5000 6000 7000 8500 9000 9500 4000 3000; do
  curl -s "http://localhost:$port/healthz" && echo "  <- :$port OK"
done
```

## 7. Smoke-test without a live phone call

You can exercise the whole booking flow with curl alone, no Twilio call
needed:

```bash
# 1. Confirm the catalog seeded
curl http://localhost:5000/services

# 2. Check availability for a service
curl "http://localhost:6000/availability?service_id=id_card_renewal&location_id=counter_1&preferred_date=2026-08-20&preferred_time=09:00-09:30"

# 3. Hold a slot
curl -X POST http://localhost:6000/hold \
  -H "Content-Type: application/json" \
  -d '{"service_id":"id_card_renewal","location_id":"counter_1","date":"2026-08-20","time_block":"09:00-09:30","call_sid":"TEST-CALL-1"}'
# -> note the returned holdId

# 4. Confirm the appointment (replace <hold_id> with the value from step 3)
curl -X POST http://localhost:7000/appointments/confirm \
  -H "Content-Type: application/json" \
  -d '{"hold_id":"<hold_id>","call_sid":"TEST-CALL-1","name":"Imtiaz Ahmed","phone_from_caller_id":"+923001234567"}'
# -> returns { trackingNumber, ... }

# 5. Generate the receipt (replace <tracking_number> from step 4)
curl -X POST http://localhost:9000/receipts/generate \
  -H "Content-Type: application/json" \
  -d '{"tracking_number":"<tracking_number>"}'
# -> returns { downloadUrl, expiresAt } — open downloadUrl in a browser to see the PDF

# 6. Validate/format the tracking number for read-back
curl "http://localhost:8500/tracking/validate?number=<tracking_number>"
curl "http://localhost:8500/tracking/readback?number=<tracking_number>"

# 7. Check status (requires the phone number on the appointment)
curl "http://localhost:9500/status/<tracking_number>?phone=%2B923001234567"

# 8. Staff moves the status forward
curl -X PUT http://localhost:9500/status/<tracking_number> \
  -H "Content-Type: application/json" \
  -d '{"to_status":"CheckedIn","staff_id":"staff_001"}'
```

## 8. Making a real phone call end-to-end (optional)

Requires real Twilio + STT/TTS + Anthropic credentials in
`telephony-gateway/.env` and `voice-agent/.env`.

```bash
# Expose telephony-gateway publicly so Twilio's webhook can reach it
ngrok http 3000
```

Then in the Twilio Console, set your phone number's "A call comes in"
webhook to `https://<your-ngrok-subdomain>.ngrok.io/voice` (POST), per
`telephony-gateway/README.md` section 1. Call the number — the full flow
(consent notice -> dialogue -> booking -> tracking number read aloud ->
SMS) should run live.

## Stopping everything

```bash
# Stop the Node services (Ctrl+C in each terminal, or):
pkill -f "npm run dev"

# Stop infrastructure:
docker compose down          # keep data
docker compose down -v       # also wipe Postgres/MinIO volumes
```
