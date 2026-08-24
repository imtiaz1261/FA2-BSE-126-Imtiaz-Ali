const { pool } = require('../db/pool');
const { withSlotLock } = require('../db/distributedLock');
const config = require('../config/env');

/**
 * Phase 1: hold_slot.
 *
 * Two independent layers of concurrency protection, deliberately not just
 * one:
 *  1. Redis distributed lock on the specific slot row — cheap, fast, and
 *     rejects contending requests quickly (a caller losing the race gets a
 *     clear "try another slot" response in milliseconds instead of
 *     queueing behind a DB transaction).
 *  2. Postgres `SELECT ... FOR UPDATE` inside a transaction — the actual
 *     correctness guarantee. Even if the Redis lock were ever bypassed
 *     (e.g. a second app instance with a network partition to Redis), the
 *     row lock plus the `chk_capacity_not_exceeded` CHECK constraint make
 *     it structurally impossible for two holds to push held+booked past
 *     capacity.
 *
 * Returns { holdId, expiresAt } on success, or throws SLOT_FULL /
 * SLOT_NOT_FOUND / SLOT_LOCK_CONTENDED for the API layer to translate into
 * a client-facing response.
 */
async function holdSlot({ serviceId, locationId, date, timeBlock, callSid }) {
  const lockKey = `${serviceId}:${locationId}:${date}:${timeBlock}`;

  return withSlotLock(lockKey, async () => {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      const { rows } = await client.query(
        `SELECT * FROM slots
         WHERE service_id = $1 AND location_id = $2 AND date = $3 AND time_block = $4
         FOR UPDATE`,
        [serviceId, locationId, date, timeBlock]
      );

      if (rows.length === 0) {
        await client.query('ROLLBACK');
        const err = new Error('SLOT_NOT_FOUND');
        err.code = 'SLOT_NOT_FOUND';
        throw err;
      }

      const slot = rows[0];
      const remaining = slot.capacity - slot.booked_count - slot.held_count;
      if (remaining <= 0) {
        await client.query('ROLLBACK');
        const err = new Error('SLOT_FULL');
        err.code = 'SLOT_FULL';
        throw err;
      }

      const expiresAt = new Date(Date.now() + config.HOLD_TTL_SECONDS * 1000);

      const holdResult = await client.query(
        `INSERT INTO slot_holds (slot_id, call_sid, status, expires_at)
         VALUES ($1, $2, 'active', $3)
         RETURNING hold_id`,
        [slot.id, callSid, expiresAt]
      );

      await client.query(
        `UPDATE slots SET held_count = held_count + 1, updated_at = now() WHERE id = $1`,
        [slot.id]
      );

      await client.query('COMMIT');

      return { holdId: holdResult.rows[0].hold_id, slotId: slot.id, expiresAt };
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      throw err;
    } finally {
      client.release();
    }
  });
}

/**
 * Phase 2: confirm_slot. Promotes an active, unexpired hold into a
 * confirmed booking. This is what the Booking Service (Module 6) calls
 * once the caller has said "yes" to the final readback.
 */
async function confirmSlot({ holdId }) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const { rows } = await client.query(
      `SELECT * FROM slot_holds WHERE hold_id = $1 FOR UPDATE`,
      [holdId]
    );

    if (rows.length === 0) {
      await client.query('ROLLBACK');
      const err = new Error('HOLD_NOT_FOUND');
      err.code = 'HOLD_NOT_FOUND';
      throw err;
    }

    const hold = rows[0];

    if (hold.status !== 'active') {
      await client.query('ROLLBACK');
      const err = new Error(`HOLD_NOT_ACTIVE:${hold.status}`);
      err.code = 'HOLD_NOT_ACTIVE';
      throw err;
    }

    if (new Date(hold.expires_at) < new Date()) {
      // Belt-and-suspenders: even if the sweeper hasn't run yet, refuse to
      // confirm an expired hold and release it right now instead.
      await client.query(
        `UPDATE slot_holds SET status = 'expired' WHERE hold_id = $1`,
        [holdId]
      );
      await client.query(
        `UPDATE slots SET held_count = GREATEST(held_count - 1, 0) WHERE id = $1`,
        [hold.slot_id]
      );
      await client.query('COMMIT');
      const err = new Error('HOLD_EXPIRED');
      err.code = 'HOLD_EXPIRED';
      throw err;
    }

    await client.query(
      `UPDATE slot_holds SET status = 'confirmed', confirmed_at = now() WHERE hold_id = $1`,
      [holdId]
    );

    await client.query(
      `UPDATE slots
       SET booked_count = booked_count + 1, held_count = held_count - 1, updated_at = now()
       WHERE id = $1`,
      [hold.slot_id]
    );

    await client.query('COMMIT');
    return { holdId, slotId: hold.slot_id, status: 'confirmed' };
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/**
 * Explicit release — called by the telephony gateway / voice agent when a
 * caller hangs up mid-negotiation (see Module 2's mid-call-hangup handling
 * and Module 3's session cleanup) rather than waiting for the TTL sweeper.
 */
async function releaseHold({ holdId }) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const { rows } = await client.query(
      `SELECT * FROM slot_holds WHERE hold_id = $1 AND status = 'active' FOR UPDATE`,
      [holdId]
    );
    if (rows.length === 0) {
      await client.query('ROLLBACK');
      return { released: false };
    }

    const hold = rows[0];
    await client.query(`UPDATE slot_holds SET status = 'released' WHERE hold_id = $1`, [holdId]);
    await client.query(
      `UPDATE slots SET held_count = GREATEST(held_count - 1, 0) WHERE id = $1`,
      [hold.slot_id]
    );
    await client.query('COMMIT');
    return { released: true };
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

module.exports = { holdSlot, confirmSlot, releaseHold };
