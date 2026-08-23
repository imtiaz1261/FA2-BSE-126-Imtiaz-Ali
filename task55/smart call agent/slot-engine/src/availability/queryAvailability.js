const { pool } = require('../db/pool');
const config = require('../config/env');

/**
 * A slot is bookable if capacity hasn't been consumed by confirmed bookings
 * or *active, unexpired* holds. held_count is only ever incremented/
 * decremented by hold/confirm/release/expire, so it stays accurate between
 * background sweeps even if an expired hold hasn't been swept yet.
 */
const AVAILABILITY_CLAUSE = '(capacity - booked_count - held_count) > 0';

/** Minutes since midnight for a "HH:MM-HH:MM" block's start, for proximity ranking. */
function blockStartMinutes(timeBlock) {
  const [start] = timeBlock.split('-');
  const [h, m] = start.split(':').map(Number);
  return h * 60 + m;
}

/**
 * Exact match: same service, date, and time_block (optionally filtered to
 * a specific location; otherwise any eligible location).
 */
async function findExactSlot({ serviceId, locationId, date, timeBlock }) {
  const params = [serviceId, date, timeBlock];
  let locationFilter = '';
  if (locationId) {
    params.push(locationId);
    locationFilter = `AND location_id = $${params.length}`;
  }

  const { rows } = await pool.query(
    `SELECT * FROM slots
     WHERE service_id = $1 AND date = $2 AND time_block = $3
       AND ${AVAILABILITY_CLAUSE}
       ${locationFilter}
     ORDER BY location_id
     LIMIT 5`,
    params
  );
  return rows;
}

/**
 * Nearest alternatives: fetches all available slots within +/-
 * NEAREST_SEARCH_DAYS of the preferred date, then ranks in JS by
 * (day distance, time-of-day distance from the preferred block) — this is
 * what lets the dialogue manager say "Tuesday at 10 is full, but I have
 * Tuesday at 11 or Wednesday at 9:30," closest options first.
 */
async function findNearestAlternatives({ serviceId, locationId, date, timeBlock }) {
  const params = [serviceId, date, config.NEAREST_SEARCH_DAYS];
  let locationFilter = '';
  if (locationId) {
    params.push(locationId);
    locationFilter = `AND location_id = $${params.length}`;
  }

  const { rows } = await pool.query(
    `SELECT *, (date - $2::date) AS day_offset
     FROM slots
     WHERE service_id = $1
       AND date BETWEEN ($2::date - $3) AND ($2::date + $3)
       AND ${AVAILABILITY_CLAUSE}
       ${locationFilter}
     ORDER BY date ASC, time_block ASC`,
    params
  );

  const preferredMinutes = blockStartMinutes(timeBlock);

  const ranked = rows
    .filter((r) => !(r.date.toISOString().slice(0, 10) === date && r.time_block === timeBlock))
    .map((r) => ({
      ...r,
      _dayDistance: Math.abs(r.day_offset),
      _timeDistance: Math.abs(blockStartMinutes(r.time_block) - preferredMinutes),
    }))
    .sort((a, b) => a._dayDistance - b._dayDistance || a._timeDistance - b._timeDistance);

  return ranked
    .slice(0, config.NEAREST_RESULTS_LIMIT)
    .map(({ _dayDistance, _timeDistance, day_offset, ...slot }) => slot);
}

/** Top-level entry point for GET /availability. */
async function queryAvailability({ serviceId, locationId, preferredDate, preferredTime }) {
  const timeBlock = preferredTime; // caller passes a valid block, e.g. "09:00-09:30"

  const exact = await findExactSlot({ serviceId, locationId, date: preferredDate, timeBlock });
  if (exact.length > 0) {
    return { exactMatch: true, slots: exact, alternatives: [] };
  }

  const alternatives = await findNearestAlternatives({
    serviceId,
    locationId,
    date: preferredDate,
    timeBlock,
  });

  return { exactMatch: false, slots: [], alternatives };
}

module.exports = { queryAvailability, findExactSlot, findNearestAlternatives };
