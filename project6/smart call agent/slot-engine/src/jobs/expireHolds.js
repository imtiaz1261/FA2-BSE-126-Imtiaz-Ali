const { pool } = require('../db/pool');
const config = require('../config/env');

/**
 * Safety net for the 2-minute hold TTL: even if the caller's session never
 * explicitly releases a hold (e.g. the telephony gateway's release call
 * fails, or a process crashes mid-call), this sweeper guarantees the
 * capacity comes back within one sweep interval of expiry.
 */
async function sweepExpiredHolds() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const { rows: expired } = await client.query(
      `SELECT hold_id, slot_id FROM slot_holds
       WHERE status = 'active' AND expires_at < now()
       FOR UPDATE SKIP LOCKED`
    );

    for (const hold of expired) {
      await client.query(`UPDATE slot_holds SET status = 'expired' WHERE hold_id = $1`, [
        hold.hold_id,
      ]);
      await client.query(
        `UPDATE slots SET held_count = GREATEST(held_count - 1, 0), updated_at = now() WHERE id = $1`,
        [hold.slot_id]
      );
    }

    await client.query('COMMIT');
    if (expired.length > 0) {
      console.log(`Swept ${expired.length} expired hold(s).`);
    }
    return expired.length;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    console.error('Hold sweep failed', err);
    return 0;
  } finally {
    client.release();
  }
}

function startHoldSweeper() {
  const interval = setInterval(sweepExpiredHolds, config.HOLD_SWEEP_INTERVAL_MS);
  interval.unref?.(); // don't keep the process alive solely for this timer
  return interval;
}

module.exports = { sweepExpiredHolds, startHoldSweeper };
