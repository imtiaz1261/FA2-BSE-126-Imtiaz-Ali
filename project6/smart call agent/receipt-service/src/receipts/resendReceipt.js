const config = require('../config/env');
const { pool } = require('../db/pool');
const { generateReceipt } = require('./generateReceipt');

async function fetchAppointment(trackingNumber) {
  const res = await fetch(`${config.BOOKING_SERVICE_BASE_URL}/appointments/${trackingNumber}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`booking-service lookup failed: ${res.status}`);
  return res.json();
}

/**
 * Self-service "resend receipt" — looks up the appointment by tracking
 * number AND verifies the caller-supplied phone number matches the one on
 * file before sending anything. This is the only authentication this
 * public-facing endpoint has, so both fields are required and phone
 * comparison is done on normalized digits only (ignoring formatting like
 * spaces, dashes, or a leading +) to avoid false negatives from harmless
 * formatting differences while still requiring a real match.
 */
function normalizePhoneForComparison(phone) {
  return (phone || '').replace(/\D/g, '');
}

async function resendReceipt({ trackingNumber, phone }) {
  const appointment = await fetchAppointment(trackingNumber);
  if (!appointment) {
    const err = new Error('APPOINTMENT_NOT_FOUND');
    err.code = 'APPOINTMENT_NOT_FOUND';
    throw err;
  }

  const providedDigits = normalizePhoneForComparison(phone);
  const onFileDigits = normalizePhoneForComparison(appointment.phone_number);

  // Compare the last 10 digits so a caller typing without a country code
  // still verifies correctly, without weakening the check to "any
  // substring match."
  const matches = providedDigits.length >= 7 && providedDigits.slice(-10) === onFileDigits.slice(-10);

  if (!matches) {
    const err = new Error('PHONE_MISMATCH');
    err.code = 'PHONE_MISMATCH';
    throw err;
  }

  const { downloadUrl, expiresAt } = await generateReceipt({ trackingNumber });

  const notifyRes = await fetch(`${config.NOTIFICATION_SERVICE_BASE_URL}/notify/receipt-resend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: appointment.phone_number, trackingNumber, downloadUrl }),
  }).catch((err) => {
    console.error('Failed to trigger receipt resend notification', err);
    return null;
  });

  await pool.query(`UPDATE receipts SET last_sent_at = now() WHERE tracking_number = $1`, [
    trackingNumber,
  ]);

  return { sent: !!notifyRes?.ok, downloadUrl, expiresAt };
}

module.exports = { resendReceipt };
