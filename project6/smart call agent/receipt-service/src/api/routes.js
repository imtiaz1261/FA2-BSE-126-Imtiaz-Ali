const express = require('express');
const { generateReceipt } = require('../receipts/generateReceipt');
const { resendReceipt } = require('../receipts/resendReceipt');

const router = express.Router();

// Called once automatically right after booking confirmation (Module 6),
// and safe to call again — returns the existing signed URL without
// regenerating the PDF unless force_regenerate is set.
router.post('/receipts/generate', async (req, res) => {
  const { tracking_number, force_regenerate } = req.body;
  if (!tracking_number) return res.status(400).json({ error: 'tracking_number is required' });

  try {
    const result = await generateReceipt({
      trackingNumber: tracking_number,
      forceRegenerate: !!force_regenerate,
    });
    res.status(201).json(result);
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'appointment_not_found' });
    }
    console.error('generateReceipt failed', err);
    res.status(500).json({ error: 'receipt_generation_failed' });
  }
});

// Self-service re-download: GET a fresh signed URL for an already-generated
// receipt, given just the tracking number. Since a signed URL only grants
// temporary access to a single, non-guessable-in-practice object key, and
// this path only returns a URL (never the phone/CNIC/name themselves),
// this is intentionally lighter-weight than /resend — no phone
// verification required just to fetch a download link for a number the
// caller already has in hand. Resending to a *phone number* (SMS/email)
// requires verification below, since that reaches a third party.
router.get('/receipts/:trackingNumber', async (req, res) => {
  try {
    const result = await generateReceipt({ trackingNumber: req.params.trackingNumber });
    res.json(result);
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'appointment_not_found' });
    }
    console.error('receipt lookup/generate failed', err);
    res.status(500).json({ error: 'receipt_lookup_failed' });
  }
});

// Self-service "Resend receipt" — requires tracking_number + phone for
// verification before sending anything to a phone number.
router.post('/receipts/resend', async (req, res) => {
  const { tracking_number, phone } = req.body;
  if (!tracking_number || !phone) {
    return res.status(400).json({ error: 'tracking_number and phone are required' });
  }

  try {
    const result = await resendReceipt({ trackingNumber: tracking_number, phone });
    res.json(result);
  } catch (err) {
    if (err.code === 'APPOINTMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'appointment_not_found' });
    }
    if (err.code === 'PHONE_MISMATCH') {
      // Deliberately vague — do not reveal whether the tracking number
      // exists but the phone was wrong, vs. reveal nothing further; avoid
      // leaking which part of the pair was incorrect.
      return res.status(403).json({ error: 'verification_failed' });
    }
    console.error('resendReceipt failed', err);
    res.status(500).json({ error: 'resend_failed' });
  }
});

module.exports = router;
