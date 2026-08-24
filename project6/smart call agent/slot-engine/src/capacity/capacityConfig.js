const { pool } = require('../db/pool');

/**
 * Sets (creating if necessary) the capacity for one service/location/date/
 * time_block. This is the primitive the Admin Console (Module 11) uses for
 * day-level overrides — e.g. reducing capacity to 0 across all blocks on a
 * public holiday, or bumping it up for an extended-hours day.
 *
 * Deliberately does NOT allow shrinking capacity below the current
 * booked_count — you cannot admin your way into overbooking a slot that
 * already has confirmed appointments.
 */
async function setSlotCapacity({ serviceId, locationId, date, timeBlock, capacity }) {
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
      const inserted = await client.query(
        `INSERT INTO slots (service_id, location_id, date, time_block, capacity)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING *`,
        [serviceId, locationId, date, timeBlock, capacity]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    }

    const existing = rows[0];
    if (capacity < existing.booked_count) {
      await client.query('ROLLBACK');
      const err = new Error(
        `Cannot set capacity (${capacity}) below existing booked_count (${existing.booked_count})`
      );
      err.code = 'CAPACITY_BELOW_BOOKED';
      throw err;
    }

    const updated = await client.query(
      `UPDATE slots SET capacity = $1, updated_at = now() WHERE id = $2 RETURNING *`,
      [capacity, existing.id]
    );
    await client.query('COMMIT');
    return updated.rows[0];
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/**
 * Bulk day-level override — e.g. "set every block for id_card_renewal at
 * counter_1 on 2026-12-25 to capacity 0" for a public holiday, without the
 * admin having to edit each time_block individually.
 */
async function setDayCapacity({ serviceId, locationId, date, capacity }) {
  const { rows: existingBlocks } = await pool.query(
    `SELECT time_block FROM slots WHERE service_id = $1 AND location_id = $2 AND date = $3`,
    [serviceId, locationId, date]
  );

  const results = [];
  for (const row of existingBlocks) {
    results.push(
      await setSlotCapacity({
        serviceId,
        locationId,
        date,
        timeBlock: row.time_block,
        capacity,
      })
    );
  }
  return results;
}

module.exports = { setSlotCapacity, setDayCapacity };
