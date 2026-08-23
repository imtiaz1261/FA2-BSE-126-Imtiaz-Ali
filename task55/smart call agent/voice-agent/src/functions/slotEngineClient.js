const config = require('../config/env');

/**
 * Thin client over the Slot Engine service from Module 1. Used two ways:
 *  1. Directly by the orchestrator (session/callSession.js) when entering
 *     CHECKING_SLOTS, to fetch real availability to read out to the caller.
 *  2. Exposed as a tool the LLM can call mid-turn if the caller asks a
 *     question like "do you have anything on Friday?" before we've
 *     formally reached the day-capture state.
 */
async function checkAvailability({ serviceType, day, time }) {
  const params = new URLSearchParams({ serviceType });
  if (day) params.set('day', day);
  if (time) params.set('time', time);

  const res = await fetch(`${config.SLOT_ENGINE_BASE_URL}/availability?${params}`);
  if (!res.ok) throw new Error(`Slot Engine error: ${res.status}`);
  return res.json(); // { slots: [{ day, time, remaining }], hasAvailability: bool }
}

async function holdSlot({ callSid, serviceType, day, time }) {
  const res = await fetch(`${config.SLOT_ENGINE_BASE_URL}/hold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ callSid, serviceType, day, time }),
  });
  if (!res.ok) throw new Error(`Slot hold failed: ${res.status}`);
  return res.json(); // { holdId, expiresAt }
}

const CHECK_AVAILABILITY_TOOL = {
  name: 'check_availability',
  description:
    'Looks up real appointment availability for a service type, optionally filtered by day/time. Use this whenever the caller asks about available days/times, or once purpose_of_visit is confirmed and you need to tell them what is open.',
  input_schema: {
    type: 'object',
    properties: {
      serviceType: { type: 'string', description: 'Normalized service type, e.g. "passport_renewal".' },
      day: { type: 'string', description: 'Optional ISO date or relative day to filter by.' },
      time: { type: 'string', description: 'Optional time filter.' },
    },
    required: ['serviceType'],
  },
};

module.exports = { checkAvailability, holdSlot, CHECK_AVAILABILITY_TOOL };
