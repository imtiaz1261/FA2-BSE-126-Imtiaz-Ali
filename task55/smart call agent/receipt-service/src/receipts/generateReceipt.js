const { pool } = require('../db/pool');
const config = require('../config/env');
const { buildReceiptPdf } = require('../pdf/buildReceiptPdf');
const { uploadReceiptPdf, getSignedDownloadUrl } = require('../storage/objectStorage');
const { getLocationDetails } = require('../locations/locationDirectory');

async function fetchAppointment(trackingNumber) {
  const res = await fetch(`${config.BOOKING_SERVICE_BASE_URL}/appointments/${trackingNumber}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`booking-service lookup failed: ${res.status}`);
  return res.json();
}

async function fetchServiceDetails(serviceId) {
  const res = await fetch(`${config.SERVICE_CATALOG_BASE_URL}/services/${serviceId}`);
  if (!res.ok) throw new Error(`service-catalog lookup failed: ${res.status}`);
  return res.json(); // { name, required_documents, ... }
}

/**
 * Generates (or regenerates) the PDF receipt for a confirmed appointment,
 * uploads it to object storage, and returns a signed download URL.
 *
 * Called once automatically right after booking confirmation (Module 6
 * triggers this as part of its post-commit flow, alongside the SMS
 * trigger), and can also be called again on-demand — e.g. from the
 * self-service portal's "Resend receipt" flow — without regenerating the
 * PDF from scratch if one already exists (see `forceRegenerate`).
 */
async function generateReceipt({ trackingNumber, forceRegenerate = false }) {
  const existing = await pool.query(
    `SELECT * FROM receipts WHERE tracking_number = $1`,
    [trackingNumber]
  );

  if (existing.rows.length > 0 && !forceRegenerate) {
    const { url, expiresAt } = await getSignedDownloadUrl(existing.rows[0].s3_key);
    return { downloadUrl: url, expiresAt, regenerated: false };
  }

  const appointment = await fetchAppointment(trackingNumber);
  if (!appointment) {
    const err = new Error('APPOINTMENT_NOT_FOUND');
    err.code = 'APPOINTMENT_NOT_FOUND';
    throw err;
  }

  const service = await fetchServiceDetails(appointment.service_id);
  const location = getLocationDetails(appointment.location_id);

  const pdfBuffer = await buildReceiptPdf({
    applicantName: appointment.caller_name,
    cnic: appointment.cnic,
    serviceName: service.name,
    requiredDocuments: service.required_documents,
    locationName: location.name,
    locationAddress: location.address,
    date: appointment.date,
    timeBlock: appointment.time_block,
    trackingNumber: appointment.tracking_number,
  });

  const s3Key = await uploadReceiptPdf(trackingNumber, pdfBuffer);

  await pool.query(
    `INSERT INTO receipts (tracking_number, s3_key, generated_at, regenerated_count)
     VALUES ($1, $2, now(), 0)
     ON CONFLICT (tracking_number) DO UPDATE SET
       s3_key = EXCLUDED.s3_key,
       generated_at = now(),
       regenerated_count = receipts.regenerated_count + 1`,
    [trackingNumber, s3Key]
  );

  const { url, expiresAt } = await getSignedDownloadUrl(s3Key);
  return { downloadUrl: url, expiresAt, regenerated: existing.rows.length > 0 };
}

module.exports = { generateReceipt };
