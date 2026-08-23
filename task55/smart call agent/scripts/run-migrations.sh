#!/usr/bin/env bash
# Applies every service's migrations to the shared Postgres database, in
# the order their foreign-key dependencies require:
#   service-catalog -> slot-engine -> tracking-service -> booking-service -> receipt-service
#
# Usage:
#   DATABASE_URL=postgresql://appuser:changeme_locally@localhost:5432/appointments ./scripts/run-migrations.sh

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "Set DATABASE_URL first, e.g.:"
  echo "  export DATABASE_URL=postgresql://appuser:changeme_locally@localhost:5432/appointments"
  exit 1
fi

MIGRATIONS=(
  "service-catalog/db/migrations/001_create_services.sql"
  "slot-engine/db/migrations/002_create_slots.sql"
  "tracking-service/db/migrations/005_create_tracking_counters.sql"
  "booking-service/db/migrations/004_create_appointments.sql"
  "receipt-service/db/migrations/006_create_receipts.sql"
  "status-service/db/migrations/008_add_status_tracking.sql"
)

for file in "${MIGRATIONS[@]}"; do
  echo "Applying $file ..."
  psql "$DATABASE_URL" -f "$file"
done

echo "All migrations applied."
