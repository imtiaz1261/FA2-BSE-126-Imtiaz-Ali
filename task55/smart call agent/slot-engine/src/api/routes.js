const express = require('express');
const { queryAvailability } = require('../availability/queryAvailability');
const { holdSlot, confirmSlot, releaseHold } = require('../reservation/reservationService');
const { setSlotCapacity, setDayCapacity } = require('../capacity/capacityConfig');

const router = express.Router();

// Called by the Voice Agent (Module 3) when checking availability, and by
// the Booking Service (Module 6) for read-model displays.
router.get('/availability', async (req, res) => {
  const { service_id, location_id, preferred_date, preferred_time } = req.query;
  if (!service_id || !preferred_date || !preferred_time) {
    return res
      .status(400)
      .json({ error: 'service_id, preferred_date, and preferred_time are required' });
  }

  try {
    const result = await queryAvailability({
      serviceId: service_id,
      locationId: location_id || null,
      preferredDate: preferred_date,
      preferredTime: preferred_time,
    });
    res.json(result);
  } catch (err) {
    console.error('availability query failed', err);
    res.status(500).json({ error: 'availability_query_failed' });
  }
});

// Phase 1: temporary reservation. Called once the caller has stated a
// preference and the dialogue manager is about to read it back for
// confirmation (Module 3's CONFIRMING_DATETIME state).
router.post('/hold', async (req, res) => {
  const { service_id, location_id, date, time_block, call_sid } = req.body;
  if (!service_id || !location_id || !date || !time_block || !call_sid) {
    return res.status(400).json({ error: 'service_id, location_id, date, time_block, call_sid are required' });
  }

  try {
    const result = await holdSlot({
      serviceId: service_id,
      locationId: location_id,
      date,
      timeBlock: time_block,
      callSid: call_sid,
    });
    res.status(201).json(result);
  } catch (err) {
    if (err.code === 'SLOT_FULL') return res.status(409).json({ error: 'slot_full' });
    if (err.code === 'SLOT_NOT_FOUND') return res.status(404).json({ error: 'slot_not_found' });
    if (err.code === 'SLOT_LOCK_CONTENDED' || err.message === 'SLOT_LOCK_CONTENDED') {
      return res.status(409).json({ error: 'slot_contended', hint: 'retry_with_different_slot' });
    }
    console.error('hold_slot failed', err);
    res.status(500).json({ error: 'hold_failed' });
  }
});

// Phase 2: commit. Called by the Booking Service once the caller confirms
// "yes" on the final readback.
router.post('/confirm', async (req, res) => {
  const { hold_id } = req.body;
  if (!hold_id) return res.status(400).json({ error: 'hold_id is required' });

  try {
    const result = await confirmSlot({ holdId: hold_id });
    res.json(result);
  } catch (err) {
    if (err.code === 'HOLD_NOT_FOUND') return res.status(404).json({ error: 'hold_not_found' });
    if (err.code === 'HOLD_EXPIRED') return res.status(410).json({ error: 'hold_expired' });
    if (err.code === 'HOLD_NOT_ACTIVE') return res.status(409).json({ error: 'hold_not_active' });
    console.error('confirm_slot failed', err);
    res.status(500).json({ error: 'confirm_failed' });
  }
});

// Explicit release — called on mid-call hangup (Module 2) or when the
// caller rejects the readback and wants a different day/time.
router.post('/release', async (req, res) => {
  const { hold_id } = req.body;
  if (!hold_id) return res.status(400).json({ error: 'hold_id is required' });

  const result = await releaseHold({ holdId: hold_id });
  res.json(result);
});

// Admin capacity management (Module 11 Admin Console calls these).
router.put('/admin/capacity', async (req, res) => {
  const { service_id, location_id, date, time_block, capacity } = req.body;
  if (!service_id || !location_id || !date || !time_block || capacity === undefined) {
    return res
      .status(400)
      .json({ error: 'service_id, location_id, date, time_block, capacity are required' });
  }

  try {
    const result = await setSlotCapacity({
      serviceId: service_id,
      locationId: location_id,
      date,
      timeBlock: time_block,
      capacity,
    });
    res.json(result);
  } catch (err) {
    if (err.code === 'CAPACITY_BELOW_BOOKED') {
      return res.status(409).json({ error: 'capacity_below_booked', message: err.message });
    }
    console.error('set_slot_capacity failed', err);
    res.status(500).json({ error: 'capacity_update_failed' });
  }
});

// Bulk day-level override, e.g. for public holidays.
router.put('/admin/capacity/day', async (req, res) => {
  const { service_id, location_id, date, capacity } = req.body;
  if (!service_id || !location_id || !date || capacity === undefined) {
    return res.status(400).json({ error: 'service_id, location_id, date, capacity are required' });
  }

  try {
    const results = await setDayCapacity({
      serviceId: service_id,
      locationId: location_id,
      date,
      capacity,
    });
    res.json({ updated: results.length, slots: results });
  } catch (err) {
    console.error('set_day_capacity failed', err);
    res.status(500).json({ error: 'day_capacity_update_failed' });
  }
});

module.exports = router;
