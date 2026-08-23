const express = require('express');
const { generateTrackingNumber } = require('../generation/generateTrackingNumber');
const { validateTrackingNumber } = require('../validation/validateTrackingNumber');
const { formatForReadback } = require('../tts/formatForReadback');

const router = express.Router();

// Called by booking-service (Module 6) as part of confirming an
// appointment. Can also be called standalone for testing/tooling.
router.post('/generate', async (req, res) => {
  const { service_id, year } = req.body;
  if (!service_id) return res.status(400).json({ error: 'service_id is required' });

  try {
    const trackingNumber = await generateTrackingNumber({ serviceId: service_id, year });
    res.status(201).json({ trackingNumber });
  } catch (err) {
    if (err.code === 'SEQUENCE_OVERFLOW') {
      console.error(err.message);
      return res.status(500).json({ error: 'sequence_overflow' });
    }
    console.error('generateTrackingNumber failed', err);
    res.status(500).json({ error: 'generation_failed', message: err.message });
  }
});

// Fast, DB-free format + checksum validation. Called by the dialogue
// manager (Module 3, status-check flow) and any web/IVR status-check form
// (Module 9) BEFORE querying the appointments table, so an obvious typo
// gets an instant, specific response.
router.get('/validate', (req, res) => {
  const { number } = req.query;
  if (!number) return res.status(400).json({ error: 'number query param is required' });

  const result = validateTrackingNumber(number);
  res.json(result);
});

// Returns the spoken-word and grouped-display forms for TTS/SMS use.
router.get('/readback', (req, res) => {
  const { number } = req.query;
  if (!number) return res.status(400).json({ error: 'number query param is required' });

  const validation = validateTrackingNumber(number);
  if (!validation.valid) {
    return res.status(400).json({ error: 'invalid_tracking_number', reason: validation.reason });
  }

  try {
    const formatted = formatForReadback(validation.parsed.normalized);
    res.json(formatted);
  } catch (err) {
    res.status(400).json({ error: 'format_failed', message: err.message });
  }
});

module.exports = router;
