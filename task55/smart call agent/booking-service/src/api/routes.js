const express = require('express');
const { confirmAppointment } = require('../confirmation/confirmAppointment');
const { captureCallerDetails } = require('../confirmation/captureCallerDetails');
const { declineSlot } = require('../confirmation/declineSlot');
const { triggerBookingConfirmationSms } = require('../notifications/notifyClient');
const { pool } = require('../db/pool');

const router = express.Router();

/**
 * Called by the Voice Agent (Module 3) only after the caller has given
 * explicit verbal confirmation ("yes"/"confirm") on the readback built by
 * dialogue/confirmationReadback.js. Never called speculatively.
 */
router.post('/appointments/confirm', async (req, res) => {
  const { hold_id, call_sid, name, cnic, phone, phone_from_caller_id } = req.body;

  if (!hold_id) {
    return res.status(400).json({ error: 'hold_id is required' });
  }

  const captured = captureCallerDetails({
    name,
    cnic,
    phone,
    phoneFromCallerId: phone_from_caller_id,
  });

  if (!captured.valid) {
    return res.status(400).json({ error: 'invalid_caller_details', details: captured.errors });
  }

  try {
    const appointment = await confirmAppointment({
      holdId: hold_id,
      callerDetails: captured.details,
      callSid: call_sid,
    });

    // Fire-and-forget, after commit — never blocks or risks the booking.
    triggerBookingConfirmationSms(appointment);

    res.status(201).json({
      trackingNumber: appointment.tracking_number,
      serviceId: appointment.service_id,
      locationId: appointment.location_id,
      date: appointment.date,
      timeBlock: appointment.time_block,
      status: appointment.status,
    });
  } catch (err) {
    switch (err.code) {
      case 'HOLD_NOT_FOUND':
        return res.status(404).json({ error: 'hold_not_found' });
      case 'HOLD_EXPIRED':
        return res.status(410).json({ error: 'hold_expired', hint: 'request_a_new_hold' });
      case 'HOLD_NOT_ACTIVE':
        return res.status(409).json({ error: 'hold_not_active', currentStatus: err.currentStatus });
      case 'TRACKING_NUMBER_GENERATION_FAILED':
        console.error('tracking number generation exhausted retries', err);
        return res.status(500).json({ error: 'tracking_number_generation_failed' });
      default:
        console.error('confirmAppointment failed', err);
        return res.status(500).json({ error: 'confirmation_failed' });
    }
  }
});

/**
 * Called when the caller says "no" to the readback. Releases the hold and
 * hands back the next best alternatives in one call, so the dialogue
 * manager can immediately continue the conversation.
 */
router.post('/appointments/decline', async (req, res) => {
  const { hold_id, service_id, location_id, preferred_date, preferred_time } = req.body;
  if (!hold_id || !service_id || !preferred_date || !preferred_time) {
    return res.status(400).json({
      error: 'hold_id, service_id, preferred_date, preferred_time are required',
    });
  }

  try {
    const alternatives = await declineSlot({
      holdId: hold_id,
      serviceId: service_id,
      locationId: location_id,
      preferredDate: preferred_date,
      preferredTime: preferred_time,
    });
    res.json(alternatives);
  } catch (err) {
    console.error('declineSlot failed', err);
    res.status(500).json({ error: 'decline_failed' });
  }
});

// Used by Module 9 (status tracking) and the Admin Console (Module 11).
router.get('/appointments/:trackingNumber', async (req, res) => {
  const { rows } = await pool.query(
    `SELECT * FROM appointments WHERE tracking_number = $1`,
    [req.params.trackingNumber]
  );
  if (rows.length === 0) return res.status(404).json({ error: 'not_found' });
  res.json(rows[0]);
});

module.exports = router;
