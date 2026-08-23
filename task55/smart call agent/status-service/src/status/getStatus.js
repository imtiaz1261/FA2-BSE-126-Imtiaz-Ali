const { pool } = require('../db/pool');
const config = require('../config/env');
const { phonesMatch } = require('../verification/verifyPhone');

async function fetchAppointment(trackingNumber) {
  const res = await fetch(`${config.BOOKING_SERVICE_BASE_URL}/appointments/${trackingNumber}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`booking-service lookup failed: ${res.status}`);
  return res.json();
}

/**
 * Privacy-safe status lookup: requires BOTH the tracking number and the
 * phone number on the appointment to match before returning anything.
 * Knowing a tracking number alone (which, per Module 7, has some
 * structure an attacker could guess/brute-force check-digit-valid values
 * for) is not sufficient to see someone else's application status.
 */
async function getStatus({ trackingNumber, phone }) {
  const appointment = await fetchAppointment(trackingNumber);
  if (!appointment) {
    const err = new Error('APPOINTMENT_NOT_FOUND');
    err.code = 'APPOINTMENT_NOT_FOUND';
    throw err;
  }

  if (!phonesMatch(phone, appointment.phone_number)) {
    const err = new Error('PHONE_MISMATCH');
    err.code = 'PHONE_MISMATCH';
    throw err;
  }

  const { rows: history } = await pool.query(
    `SELECT from_status, to_status, staff_id, note, changed_at
     FROM status_history
     WHERE tracking_number = $1
     ORDER BY changed_at ASC`,
    [trackingNumber]
  );

  return {
    trackingNumber,
    currentStatus: appointment.status,
    serviceId: appointment.service_id,
    date: appointment.date,
    timeBlock: appointment.time_block,
    history,
  };
}

module.exports = { getStatus };
