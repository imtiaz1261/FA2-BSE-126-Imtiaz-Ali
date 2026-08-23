const { pool } = require('../db/pool');
const config = require('../config/env');

/**
 * One-time / periodic bootstrap: generates slot rows for every time_block
 * in business hours, for a service/location, across a date range, at the
 * default capacity. Skips (does not overwrite) any slot that already
 * exists, so re-running this to extend the calendar forward never clobbers
 * admin-configured capacity overrides on existing dates.
 *
 * Usage: node src/scripts/generateSlots.js <service_id> <location_id> <days_ahead>
 */
function enumerateTimeBlocks() {
  const [startH, startM] = config.DEFAULT_DAY_START.split(':').map(Number);
  const [endH, endM] = config.DEFAULT_DAY_END.split(':').map(Number);
  const blocks = [];

  let cursor = startH * 60 + startM;
  const end = endH * 60 + endM;

  while (cursor + config.DEFAULT_BLOCK_MINUTES <= end) {
    const fmt = (mins) =>
      `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`;
    blocks.push(`${fmt(cursor)}-${fmt(cursor + config.DEFAULT_BLOCK_MINUTES)}`);
    cursor += config.DEFAULT_BLOCK_MINUTES;
  }
  return blocks;
}

async function generateSlots({ serviceId, locationId, daysAhead = 30 }) {
  const blocks = enumerateTimeBlocks();
  let created = 0;

  for (let d = 0; d < daysAhead; d++) {
    const date = new Date();
    date.setDate(date.getDate() + d);
    const dateStr = date.toISOString().slice(0, 10);

    for (const timeBlock of blocks) {
      const result = await pool.query(
        `INSERT INTO slots (service_id, location_id, date, time_block, capacity)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (service_id, location_id, date, time_block) DO NOTHING
         RETURNING id`,
        [serviceId, locationId, dateStr, timeBlock, config.DEFAULT_CAPACITY_PER_BLOCK]
      );
      if (result.rows.length > 0) created++;
    }
  }

  return { created };
}

if (require.main === module) {
  const [, , serviceId, locationId, daysAheadArg] = process.argv;
  if (!serviceId || !locationId) {
    console.error('Usage: node generateSlots.js <service_id> <location_id> [days_ahead]');
    process.exit(1);
  }
  generateSlots({ serviceId, locationId, daysAhead: parseInt(daysAheadArg || '30', 10) })
    .then((res) => {
      console.log(`Created ${res.created} new slot rows.`);
      process.exit(0);
    })
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}

module.exports = { generateSlots, enumerateTimeBlocks };
