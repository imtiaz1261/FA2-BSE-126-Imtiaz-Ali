const config = require('../config/env');
const { getStatus } = require('../status/getStatus');
const { STATUS_DESCRIPTIONS } = require('../voice/statusReadback');

/**
 * Extracts a candidate tracking number from free-form SMS text (citizens
 * will text things like "status IDR-2026-004821-7" or just the bare
 * number) and validates it via tracking-service (Module 7) BEFORE ever
 * touching the database — same fail-fast principle as everywhere else the
 * tracking number is consumed.
 */
async function extractAndValidateTrackingNumber(smsBody) {
  const candidateMatch = /[A-Z]{3}-\d{4}-\d{6}-\d/i.exec(smsBody || '');
  if (!candidateMatch) return { valid: false, reason: 'no_tracking_number_found' };

  const res = await fetch(
    `${config.TRACKING_SERVICE_BASE_URL}/tracking/validate?number=${encodeURIComponent(candidateMatch[0])}`
  );
  if (!res.ok) return { valid: false, reason: 'validation_service_error' };
  const result = await res.json();
  if (!result.valid) return { valid: false, reason: result.reason };
  return { valid: true, trackingNumber: result.parsed.normalized };
}

/**
 * Builds the SMS reply text. Privacy verification here uses the SMS
 * sender's own phone number (Twilio's `From` on the inbound webhook) as
 * the phone to check against the appointment on file — a citizen texting
 * in from the same number they booked with is exactly the "phone number
 * verification for privacy" the design brief calls for, with no extra
 * step required from them.
 */
async function handleInboundStatusSms({ from, body }) {
  const extraction = await extractAndValidateTrackingNumber(body);
  if (!extraction.valid) {
    return 'We could not find a valid tracking number in your message. Please text your tracking number, e.g. IDR-2026-004821-7.';
  }

  try {
    const status = await getStatus({ trackingNumber: extraction.trackingNumber, phone: from });
    const description =
      STATUS_DESCRIPTIONS[status.currentStatus]?.en || 'Status could not be determined.';
    return `Tracking ${status.trackingNumber}: ${description}`;
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return `We could not find an appointment for ${extraction.trackingNumber}. Please check the number and try again.`;
    }
    if (err.code === 'PHONE_MISMATCH') {
      // Text from the number the appointment was booked with instead.
      return 'For your privacy, please text this tracking number from the phone number used to book the appointment.';
    }
    console.error('handleInboundStatusSms failed', err);
    return 'Sorry, we could not check your status right now. Please try again shortly.';
  }
}

module.exports = { handleInboundStatusSms, extractAndValidateTrackingNumber };
