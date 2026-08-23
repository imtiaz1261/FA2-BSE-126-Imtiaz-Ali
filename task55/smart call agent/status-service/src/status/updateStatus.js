const { pool } = require('../db/pool');
const config = require('../config/env');
const { validateTransition, NOTIFY_ON_STATUSES } = require('./statusModel');
const { triggerStatusMilestoneSms } = require('../notifications/notifyClient');

async function fetchAppointment(trackingNumber) {
  const res = await fetch(`${config.BOOKING_SERVICE_BASE_URL}/appointments/${trackingNumber}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`booking-service lookup failed: ${res.status}`);
  return res.json();
}

/**
 * Applies a staff-driven (or, in principle, system-driven) status
 * transition, atomically: updates `appointments.status` and appends the
 * `status_history` row in one transaction, so a status change and its
 * audit-trail entry can never disagree.
 *
 * This is the hook Module 11 (Admin/Staff Console) calls as staff scan a
 * document, mark an application processed, etc.
 */
async function updateStatus({ trackingNumber, toStatus, staffId, note }) {
  const appointment = await fetchAppointment(trackingNumber);
  if (!appointment) {
    const err = new Error('APPOINTMENT_NOT_FOUND');
    err.code = 'APPOINTMENT_NOT_FOUND';
    throw err;
  }

  const fromStatus = appointment.status;
  const transitionCheck = validateTransition(fromStatus, toStatus);
  if (!transitionCheck.valid) {
    const err = new Error(`INVALID_TRANSITION:${transitionCheck.reason}`);
    err.code = 'INVALID_TRANSITION';
    err.reason = transitionCheck.reason;
    throw err;
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // appointments is owned by booking-service's schema, but per Module 1's
    // shared-database architecture, status-service updates it directly here
    // in the same transaction as the history row — the same justification
    // booking-service used for its own atomic confirm.
    await client.query(
      `UPDATE appointments SET status = $1, updated_at = now() WHERE tracking_number = $2`,
      [toStatus, trackingNumber]
    );

    await client.query(
      `INSERT INTO status_history (tracking_number, from_status, to_status, staff_id, note)
       VALUES ($1, $2, $3, $4, $5)`,
      [trackingNumber, fromStatus, toStatus, staffId || null, note || null]
    );

    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }

  // Fire the milestone SMS only after commit succeeds, and only for
  // citizen-relevant milestones.
  if (NOTIFY_ON_STATUSES.has(toStatus)) {
    triggerStatusMilestoneSms({
      phone: appointment.phone_number,
      trackingNumber,
      status: toStatus,
      serviceId: appointment.service_id,
    });
  }

  return { trackingNumber, fromStatus, toStatus };
}

module.exports = { updateStatus };
