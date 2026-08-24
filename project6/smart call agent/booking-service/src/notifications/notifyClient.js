const config = require('../config/env');

/**
 * Triggers the Notification Service (Module 10) once an appointment is
 * durably committed. Deliberately called AFTER the confirmation
 * transaction commits (see confirmation/confirmAppointment.js) — never
 * inside it — so a slow or failing SMS provider can never roll back an
 * otherwise-successful booking.
 *
 * Failures here are logged, not thrown: the appointment is already
 * confirmed and real regardless of whether the SMS goes out immediately.
 * The Notification Service is expected to retry on its own; this call is
 * just the trigger, not the delivery guarantee.
 */
async function triggerBookingConfirmationSms(appointment) {
  try {
    const res = await fetch(`${config.NOTIFICATION_SERVICE_BASE_URL}/notify/booking-confirmed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: appointment.phone_number,
        trackingNumber: appointment.tracking_number,
        serviceId: appointment.service_id,
        date: appointment.date,
        timeBlock: appointment.time_block,
      }),
    });
    if (!res.ok) {
      console.error(`Notification trigger failed for ${appointment.tracking_number}: ${res.status}`);
    }
  } catch (err) {
    console.error(`Notification trigger error for ${appointment.tracking_number}`, err);
  }
}

module.exports = { triggerBookingConfirmationSms };
