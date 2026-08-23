const { createClient } = require('redis');
const config = require('../config/env');

const client = createClient({ url: config.REDIS_URL });
client.on('error', (err) => console.error('Redis error', err));
client.connect();

const SESSION_TTL_SECONDS = 60 * 30; // 30 min safety net, well beyond any real call

function key(callSid) {
  return `call-session:${callSid}`;
}

async function createSession(callSid, initial) {
  await client.set(key(callSid), JSON.stringify(initial), { EX: SESSION_TTL_SECONDS });
}

async function getSession(callSid) {
  const raw = await client.get(key(callSid));
  return raw ? JSON.parse(raw) : null;
}

async function updateSession(callSid, patch) {
  const current = (await getSession(callSid)) || {};
  const next = { ...current, ...patch };
  await client.set(key(callSid), JSON.stringify(next), { EX: SESSION_TTL_SECONDS });
  return next;
}

async function incrementRetries(callSid) {
  const session = await getSession(callSid);
  const retries = (session?.retries || 0) + 1;
  return updateSession(callSid, { retries });
}

async function endSession(callSid) {
  await client.del(key(callSid));
}

module.exports = { createSession, getSession, updateSession, incrementRetries, endSession };
