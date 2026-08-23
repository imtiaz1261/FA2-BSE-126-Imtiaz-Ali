const config = require('../config/env');

/**
 * Called when the dialogue manager's readback gets a "no" instead of a
 * confirmation. Releases the hold immediately (freeing capacity for other
 * callers right away, rather than waiting out the TTL) and re-queries the
 * Slot Availability Engine (Module 5) for the next best options so the
 * dialogue manager can offer alternatives without a dead end.
 */
async function declineSlot({ holdId, serviceId, locationId, preferredDate, preferredTime }) {
  const releaseRes = await fetch(`${config.SLOT_ENGINE_BASE_URL}/release`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hold_id: holdId }),
  });
  if (!releaseRes.ok) {
    throw new Error(`Failed to release hold ${holdId}: ${releaseRes.status}`);
  }

  const params = new URLSearchParams({
    service_id: serviceId,
    preferred_date: preferredDate,
    preferred_time: preferredTime,
  });
  if (locationId) params.set('location_id', locationId);

  const availabilityRes = await fetch(`${config.SLOT_ENGINE_BASE_URL}/availability?${params}`);
  if (!availabilityRes.ok) {
    throw new Error(`Availability re-query failed: ${availabilityRes.status}`);
  }

  return availabilityRes.json(); // { exactMatch, slots, alternatives }
}

module.exports = { declineSlot };
