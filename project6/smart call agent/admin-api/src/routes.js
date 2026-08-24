const express = require('express');
const { login, verifyToken, requireRole } = require('./auth');
const { appointments, capacityConfig, analyticsSnapshot, statusPipeline } = require('./mockStore');

const router = express.Router();
const voiceSessions = new Map();
const appointmentServices = [
  { id: 'svc-001', name: 'ID Card Renewal', keywords: ['renew', 'id card'] },
  { id: 'svc-002', name: 'New ID Card', keywords: ['new id', 'first id card'] },
  { id: 'svc-003', name: 'Child Registration', keywords: ['child', 'birth registration'] },
  { id: 'svc-004', name: 'Passport Service', keywords: ['passport'] },
];
function findRequestedService(command) { const lower = command.toLowerCase(); return appointmentServices.find((service) => service.keywords.some((keyword) => lower.includes(keyword))); }
function slotsFor(service, date) { const slotTimes = date === '2026-08-24' ? ['09:30-10:00', '11:00-11:30', '14:00-14:30'] : ['09:00-09:30', '10:00-10:30', '13:00-13:30']; return slotTimes.map((timeBlock, index) => ({ serviceId: service.id, serviceName: service.name, locationId: 'loc-01', locationName: 'Lahore Central Desk', date, timeBlock, available: 4 - index })); }
function formatSlots(slots) { return slots.map((slot) => `${slot.date} at ${slot.timeBlock}`).join(', '); }
function requestedDate(command, currentDate) { const isoDate = command.match(/\b2026-\d{2}-\d{2}\b/); if (isoDate) return isoDate[0]; if (/another day|tomorrow|next day|24th/i.test(command)) return '2026-08-24'; return currentDate || '2026-08-23'; }

function getUserFromToken(req) {
  const authHeader = req.headers.authorization || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : null;
  if (!token) {
    return null;
  }

  try {
    return verifyToken(token);
  } catch (err) {
    return null;
  }
}

function requireAuth(req, res, next) {
  const user = getUserFromToken(req);
  if (!user) {
    return res.status(401).json({ error: 'unauthorized', message: 'Valid JWT required' });
  }
  req.user = user;
  return next();
}

router.post('/auth/login', (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ error: 'email and password are required' });
  }

  try {
    const result = login({ email, password });
    return res.json(result);
  } catch (err) {
    return res.status(err.statusCode || 401).json({ error: 'invalid_credentials', message: err.message });
  }
});

router.get('/me', requireAuth, (req, res) => {
  res.json({ user: { id: req.user.sub, role: req.user.role, email: req.user.email } });
});

function buildVoiceReply(commandText) {
  const command = (commandText || '').trim();
  const lower = command.toLowerCase();

  if (!command) {
    return 'Please say or type a service request so I can help you.';
  }

  if (lower.includes('passport')) {
    return 'Passport appointments are available this week. Please proceed to the next available slot and confirm your preferred date.';
  }

  if (lower.includes('renew') || lower.includes('id card')) {
    return 'Your ID card renewal can be booked online. I can help you select the next available appointment slot.';
  }

  if (lower.includes('check in')) {
    return 'Your appointment is checked in successfully. Please show your tracking number and identity document at the counter.';
  }

  if (lower.includes('status')) {
    return 'Your application status is in progress. The service desk will notify you when it is ready for collection.';
  }

  return 'I understood your request. This is a smart call agent response in text and voice mode.';
}

router.post('/voice/command', requireAuth, (req, res) => {
  const command = (req.body?.command || '').trim();
  const sessionKey = req.user.sub;
  const session = voiceSessions.get(sessionKey) || {};
  const service = findRequestedService(command);
  const statusNumber = command.match(/TRK-\d+/i);
  if (statusNumber && /status|track|check/i.test(command)) {
    const appointment = appointments.find((item) => item.trackingNumber.toLowerCase() === statusNumber[0].toLowerCase());
    const response = appointment
      ? `Booking ${appointment.trackingNumber} is currently ${appointment.status}. It is scheduled for ${appointment.slotDate} at ${appointment.timeBlock}.`
      : `I could not find a booking with ID ${statusNumber[0].toUpperCase()}.`;
    return res.json({ command, textResponse: response, spokenResponse: response, state: appointment ? 'status_found' : 'status_not_found', booking: appointment });
  }

  if (service) {
    voiceSessions.set(sessionKey, { service, date: '2026-08-23', slots: [] });
    const response = `I can help with ${service.name}. Ask me to show available slots, or tell me the day you prefer.`;
    return res.json({ command, textResponse: response, spokenResponse: response, state: 'service_selected', service });
  }
  if (session.pendingSlot) {
    const phoneMatch = command.match(/\+?\d[\d\s-]{8,}\d/);
    const nameMatch = command.match(/(?:my name is|name is|i am)\s+([A-Za-z][A-Za-z .'-]{1,60}?)(?:\s+(?:and )?(?:my )?(?:phone|number)|$)/i);
    const name = nameMatch?.[1]?.trim();
    const phone = phoneMatch?.[0]?.replace(/[\s-]/g, '');
    if (!name || !phone) {
      const response = 'To complete your booking, please provide both your full name and phone number. For example: My name is Ali Khan and my phone number is +923001234567.';
      return res.json({ command, textResponse: response, spokenResponse: response, state: 'awaiting_contact_details' });
    }
    const selectedSlot = session.pendingSlot;
    const trackingNumber = `TRK-${String(1000 + appointments.length + 1)}`;
    const appointment = { id: `appt-${trackingNumber.slice(4)}`, trackingNumber, applicantName: name, phoneNumber: phone, serviceId: selectedSlot.serviceId, serviceName: selectedSlot.serviceName, locationId: selectedSlot.locationId, locationName: selectedSlot.locationName, slotDate: selectedSlot.date, timeBlock: selectedSlot.timeBlock, status: 'Booked', createdAt: new Date().toISOString() };
    appointments.push(appointment); voiceSessions.delete(sessionKey);
    const response = `Thank you, ${name}. Your ${selectedSlot.serviceName} appointment is booked for ${selectedSlot.date} at ${selectedSlot.timeBlock}. Your booking ID is ${trackingNumber}.`;
    return res.status(201).json({ command, textResponse: response, spokenResponse: response, state: 'booked', booking: appointment });
  }
  if (!session.service) {
    const response = 'Please tell me what you need, for example: I want to renew my ID card.';
    return res.json({ command, textResponse: response, spokenResponse: response, state: 'awaiting_service' });
  }
  const date = requestedDate(command, session.date);
  const asksForSlots = /available|slot|show|another day|tomorrow|next day|24th|2026-\d{2}-\d{2}/i.test(command);
  if (asksForSlots && !/\bbook\b|confirm|reserve/i.test(command)) {
    const slots = slotsFor(session.service, date);
    voiceSessions.set(sessionKey, { ...session, date, slots });
    const response = `Available ${session.service.name} slots for ${date}: ${formatSlots(slots)}. Say "book ${slots[0].timeBlock}" to reserve one, or ask for another day.`;
    return res.json({ command, textResponse: response, spokenResponse: response, state: 'slots_shown', service: session.service, slots });
  }
  if (/\bbook\b|confirm|reserve/i.test(command)) {
    const slots = session.slots?.length ? session.slots : slotsFor(session.service, date);
    const selectedSlot = slots.find((slot) => command.includes(slot.timeBlock)) || slots[0];
    voiceSessions.set(sessionKey, { ...session, date, slots, pendingSlot: selectedSlot });
    const response = `You selected ${selectedSlot.date} at ${selectedSlot.timeBlock}. Before I book it, please tell me your full name and phone number.`;
    return res.json({ command, textResponse: response, spokenResponse: response, state: 'awaiting_contact_details', selectedSlot });
  }
  const response = `I have your ${session.service.name} request. Ask me to show available slots, choose another day, or book a shown slot.`;
  return res.json({ command, textResponse: response, spokenResponse: response, state: 'awaiting_slot_request', service: session.service });
});

router.get('/dashboard', requireAuth, (req, res) => {
  const sorted = [...appointments].sort((a, b) => a.slotDate.localeCompare(b.slotDate));
  res.json({ appointments: sorted, dashboard: { total: sorted.length, checkedIn: sorted.filter((a) => a.status === 'CheckedIn').length } });
});

router.post('/appointments/:trackingNumber/check-in', requireAuth, (req, res) => {
  const appointment = appointments.find((item) => item.trackingNumber === req.params.trackingNumber);
  if (!appointment) {
    return res.status(404).json({ error: 'appointment_not_found' });
  }

  appointment.status = 'CheckedIn';
  appointment.checkedInAt = new Date().toISOString();

  return res.json({
    trackingNumber: appointment.trackingNumber,
    status: appointment.status,
    updatedAt: appointment.checkedInAt,
    message: `Checked in ${appointment.applicantName}`,
  });
});

router.put('/appointments/:trackingNumber/status', requireAuth, (req, res) => {
  const appointment = appointments.find((item) => item.trackingNumber === req.params.trackingNumber);
  const { to_status } = req.body || {};

  if (!appointment) {
    return res.status(404).json({ error: 'appointment_not_found' });
  }

  if (!to_status) {
    return res.status(400).json({ error: 'to_status is required' });
  }

  const currentIndex = statusPipeline.indexOf(appointment.status);
  const nextIndex = statusPipeline.indexOf(to_status);
  if (nextIndex === -1 || nextIndex < currentIndex) {
    return res.status(409).json({ error: 'invalid_transition', reason: 'Status cannot move backwards or to an unknown value' });
  }

  const previousStatus = appointment.status;
  appointment.status = to_status;

  return res.json({
    trackingNumber: appointment.trackingNumber,
    fromStatus: previousStatus,
    toStatus: to_status,
    updatedAt: new Date().toISOString(),
    staffId: req.user.sub,
  });
});

router.get('/capacity', requireAuth, (req, res) => {
  res.json({ slots: capacityConfig });
});

router.put('/capacity', requireAuth, requireRole('admin'), (req, res) => {
  const { serviceId, locationId, date, timeBlock, capacity } = req.body || {};

  if (!serviceId || !locationId || !date || !timeBlock || capacity === undefined) {
    return res.status(400).json({ error: 'serviceId, locationId, date, timeBlock and capacity are required' });
  }

  const slotIndex = capacityConfig.findIndex(
    (item) => item.serviceId === serviceId && item.locationId === locationId && item.date === date && item.timeBlock === timeBlock,
  );

  if (slotIndex === -1) {
    capacityConfig.push({
      serviceId,
      serviceName: 'Custom Service',
      locationId,
      locationName: 'Custom Location',
      date,
      timeBlock,
      capacity,
      booked: 0,
    });
    return res.status(201).json({ updated: true, slot: capacityConfig[capacityConfig.length - 1] });
  }

  const slot = capacityConfig[slotIndex];
  if (capacity < slot.booked) {
    return res.status(409).json({ error: 'capacity_below_booked', message: `Capacity cannot be below current bookings (${slot.booked})` });
  }

  slot.capacity = capacity;
  return res.json({ updated: true, slot });
});

router.get('/analytics', requireAuth, (req, res) => {
  res.json(analyticsSnapshot);
});

module.exports = router;
