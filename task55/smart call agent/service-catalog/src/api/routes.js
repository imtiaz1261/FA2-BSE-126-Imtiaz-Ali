const express = require('express');
const { listServices, getServiceById } = require('../catalog/catalogStore');
const { classifyPurpose } = require('../classification/classifyPurpose');

const router = express.Router();

// Used by: Admin Console (Module 11) to display/manage the catalog,
// and by the Booking Service (Module 6) to look up duration/locations.
router.get('/services', async (req, res) => {
  const services = await listServices({ activeOnly: req.query.all !== 'true' });
  res.json({ services });
});

router.get('/services/:serviceId', async (req, res) => {
  const service = await getServiceById(req.params.serviceId);
  if (!service) return res.status(404).json({ error: 'not_found' });
  res.json(service);
});

// Called by the Voice Agent's dialogue manager (Module 3) when the caller
// states their purpose of visit, in place of / alongside its own
// free-text extraction — this endpoint is the source of truth for mapping
// to a real service_id with documents and duration attached.
router.post('/classify', async (req, res) => {
  const { utterance, language } = req.body;
  if (!utterance || !utterance.trim()) {
    return res.status(400).json({ error: 'utterance is required' });
  }

  try {
    const result = await classifyPurpose({ utterance, language: language || 'en' });
    res.json(result);
  } catch (err) {
    console.error('classification error', err);
    res.status(502).json({ error: 'classification_failed' });
  }
});

module.exports = router;
