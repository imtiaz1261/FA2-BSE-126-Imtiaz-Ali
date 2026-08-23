const { pool } = require('../db/pool');
const { getPrefixForService } = require('./servicePrefixes');
const { computeCheckDigit } = require('../checksum/checkDigit');

/**
 * Generates a unique tracking number:
 *   [SERVICE-PREFIX]-[YEAR]-[6-DIGIT SEQUENCE]-[CHECK-DIGIT]
 *   e.g. IDR-2026-004821-7
 *
 * Gap-free, atomic sequence generation per (prefix, year): the single
 * `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` statement is executed
 * atomically by Postgres, which takes an internal row lock for the
 * duration — concurrent bookings for the same service in the same year are
 * naturally serialized by the database itself, with no explicit
 * application-level locking needed and no possibility of two callers
 * getting the same sequence number.
 *
 * Accepts an optional `client` (an already-open pg client/transaction) so
 * booking-service's atomic confirmation transaction (Module 6) can call
 * this as part of its own transaction — if that outer transaction rolls
 * back, this increment rolls back with it, so a failed booking never
 * burns a sequence number. If no client is passed, runs against the pool
 * directly (fine for standalone use, e.g. via the HTTP API below).
 */
async function generateTrackingNumber({ serviceId, year, client }) {
  const prefix = getPrefixForService(serviceId);
  const targetYear = year || new Date().getFullYear();
  const db = client || pool;

  const { rows } = await db.query(
    `INSERT INTO tracking_counters (prefix, year, seq)
     VALUES ($1, $2, 1)
     ON CONFLICT (prefix, year) DO UPDATE SET seq = tracking_counters.seq + 1, updated_at = now()
     RETURNING seq`,
    [prefix, targetYear]
  );

  const seq = rows[0].seq;
  if (seq > 999999) {
    const err = new Error(`Sequence overflow for ${prefix}-${targetYear}: ${seq} exceeds 999999`);
    err.code = 'SEQUENCE_OVERFLOW';
    throw err;
  }

  const sequenceStr = String(seq).padStart(6, '0');
  const checkDigit = computeCheckDigit({ prefix, year: String(targetYear), sequence: sequenceStr });

  return `${prefix}-${targetYear}-${sequenceStr}-${checkDigit}`;
}

module.exports = { generateTrackingNumber };
