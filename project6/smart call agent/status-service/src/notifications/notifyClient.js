const config = require('../config/env');

/**
 * Fires the proactive milestone SMS. Called AFTER the status transition is
 * committed (see status/updateStatus.js) — same pattern as booking-service
 * and receipt-service: a notification failure must never undo or block a
 * real, already-committed status change. Logged, not thrown.
 */
async function triggerStatusMilestoneSms({ phone, trackingNumber, status, serviceId }) {
  try {
    const res = await fetch(`${config.NOTIFICATION_SERVICE_BASE_URL}/notify/status-milestone`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, trackingNumber, status, serviceId }),
    });
    if (!res.ok) {
      console.error(`Milestone notification failed for ${trackingNumber} (${status}): ${res.status}`);
    }
  } catch (err) {
    console.error(`Milestone notification error for ${trackingNumber} (${status})`, err);
  }
}

module.exports = { triggerStatusMilestoneSms };
