const { pool } = require('../db/pool');
const { generateTrackingNumber } = require('../tracking/generateTrackingNumber');
const config = require('../config/env');

/**
 * Confirms a held slot into a permanent appointment, atomically.
 *
 * Why this runs as one local Postgres transaction rather than an HTTP call
 * to the Slot Engine (Module 5) followed by a separate insert here: the
 * design brief requires "atomically: increment booked_count, insert the
 * appointment row, generate the tracking number" — true atomicity across
 * two writes is only guaranteed inside a single transaction. Per Module 1's
 * architecture ("no private database — all persistent state lives in the
 * shared PostgreSQL instance"), booking-service and slot-engine share the
 * same Postgres schema, so this transaction touches `slot_holds` and
 * `slots` directly alongside the new `appointments` row, instead of
 * attempting a distributed two-phase commit across services.
 * `POST /hold` and `POST /release` still go through the Slot Engine's own
 * HTTP API (src/api/routes.js) since those are reversible, non-critical
 * operations already protected by the hold TTL — only the irreversible
 * commit path needs this stronger guarantee.
 *
 * SMS notification (Module 10) is deliberately triggered AFTER commit,
 * never inside the transaction — a slow/failed network call must never
 * hold a database transaction open or cause a rollback of an otherwise
 * successful booking.
 */
async function confirmAppointment({ holdId, callerDetails, callSid }) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const { rows: holdRows } = await client.query(
      `SELECT h.*, s.service_id, s.location_id, s.date, s.time_block
       FROM slot_holds h
       JOIN slots s ON s.id = h.slot_id
       WHERE h.hold_id = $1
       FOR UPDATE OF h, s`,
      [holdId]
    );

    if (holdRows.length === 0) {
      await client.query('ROLLBACK');
      throw makeError('HOLD_NOT_FOUND');
    }

    const hold = holdRows[0];

    if (hold.status !== 'active') {
      await client.query('ROLLBACK');
      throw makeError('HOLD_NOT_ACTIVE', { currentStatus: hold.status });
    }

    if (new Date(hold.expires_at) < new Date()) {
      // Expired but not yet swept — clean it up and refuse, rather than
      // silently confirming a slot that may have already been re-offered
      // to someone else.
      await client.query(`UPDATE slot_holds SET status = 'expired' WHERE hold_id = $1`, [holdId]);
      await client.query(
        `UPDATE slots SET held_count = GREATEST(held_count - 1, 0) WHERE id = $1`,
        [hold.slot_id]
      );
      await client.query('COMMIT'); // commit the cleanup, but this call still fails
      throw makeError('HOLD_EXPIRED');
    }

    // 1. Promote the hold.
    await client.query(
      `UPDATE slot_holds SET status = 'confirmed', confirmed_at = now() WHERE hold_id = $1`,
      [holdId]
    );

    // 2. Increment booked_count / decrement held_count on the slot. The
    //    `chk_capacity_not_exceeded` CHECK constraint on `slots` makes this
    //    fail loudly (and roll back everything) if capacity bookkeeping
    //    was ever violated upstream — belt-and-suspenders.
    await client.query(
      `UPDATE slots
       SET booked_count = booked_count + 1, held_count = held_count - 1, updated_at = now()
       WHERE id = $1`,
      [hold.slot_id]
    );

    // 3. Generate a tracking number and insert the appointment row,
    //    retrying on the rare collision (unique constraint on
    //    tracking_number) rather than failing the whole booking.
    let appointment = null;
    let lastError = null;
    for (let attempt = 0; attempt < config.TRACKING_NUMBER_MAX_RETRIES; attempt++) {
      const trackingNumber = generateTrackingNumber(hold.service_id, hold.date.toISOString().slice(0, 10));
      try {
        const { rows } = await client.query(
          `INSERT INTO appointments
             (tracking_number, service_id, location_id, date, time_block,
              slot_id, hold_id, caller_name, cnic, phone_number, call_sid, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'confirmed')
           RETURNING *`,
          [
            trackingNumber,
            hold.service_id,
            hold.location_id,
            hold.date,
            hold.time_block,
            hold.slot_id,
            holdId,
            callerDetails.name,
            callerDetails.cnic,
            callerDetails.phone,
            callSid || null,
          ]
        );
        appointment = rows[0];
        break;
      } catch (err) {
        if (err.code === '23505') {
          // unique_violation on tracking_number — regenerate and retry
          lastError = err;
          continue;
        }
        throw err; // any other error aborts the transaction immediately
      }
    }

    if (!appointment) {
      await client.query('ROLLBACK');
      throw makeError('TRACKING_NUMBER_GENERATION_FAILED', { cause: lastError?.message });
    }

    await client.query('COMMIT');
    return appointment;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

function makeError(code, extra = {}) {
  const err = new Error(code);
  err.code = code;
  Object.assign(err, extra);
  return err;
}

module.exports = { confirmAppointment };
