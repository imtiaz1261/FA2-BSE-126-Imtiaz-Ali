const express = require('express');
const twilio = require('twilio');
const { getStatus } = require('../status/getStatus');
const { updateStatus } = require('../status/updateStatus');
const { handleInboundStatusSms } = require('../sms/smsKeywordHandler');

const router = express.Router();
const MessagingResponse = twilio.twiml.MessagingResponse;

/**
 * Privacy-safe status lookup — requires both tracking_number and phone.
 * Called by:
 *  - The Voice Agent's check-status dialogue flow (using the caller's
 *    caller-ID phone automatically, no extra question needed)
 *  - A self-service web status-check page (phone entered by the citizen)
 */
router.get('/status/:trackingNumber', async (req, res) => {
  const { phone } = req.query;
  if (!phone) return res.status(400).json({ error: 'phone query param is required' });

  try {
    const result = await getStatus({ trackingNumber: req.params.trackingNumber, phone });
    res.json(result);
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'appointment_not_found' });
    }
    if (err.code === 'PHONE_MISMATCH') {
      return res.status(403).json({ error: 'verification_failed' });
    }
    console.error('getStatus failed', err);
    res.status(500).json({ error: 'status_lookup_failed' });
  }
});

/**
 * Staff-driven status update — the hook Module 11 (Admin/Staff Console)
 * calls as an application physically progresses. staff_id is required so
 * every transition is attributable in status_history.
 */
router.put('/status/:trackingNumber', async (req, res) => {
  const { to_status, staff_id, note } = req.body;
  if (!to_status || !staff_id) {
    return res.status(400).json({ error: 'to_status and staff_id are required' });
  }

  try {
    const result = await updateStatus({
      trackingNumber: req.params.trackingNumber,
      toStatus: to_status,
      staffId: staff_id,
      note,
    });
    res.json(result);
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'appointment_not_found' });
    }
    if (err.code === 'INVALID_TRANSITION') {
      return res.status(409).json({ error: 'invalid_transition', reason: err.reason });
    }
    console.error('updateStatus failed', err);
    res.status(500).json({ error: 'status_update_failed' });
  }
});

/**
 * Twilio inbound-SMS webhook — configure this URL as the "A message
 * comes in" webhook on the citizen-services SMS-capable number (can be
 * the same Twilio number as the voice line). Twilio POSTs
 * application/x-www-form-urlencoded with From/Body; this must be mounted
 * behind express.urlencoded() (see server.js).
 */
router.post('/sms/inbound', async (req, res) => {
  const { From, Body } = req.body;
  const replyText = await handleInboundStatusSms({ from: From, body: Body });

  const twiml = new MessagingResponse();
  twiml.message(replyText);
  res.type('text/xml').send(twiml.toString());
});

module.exports = router;
