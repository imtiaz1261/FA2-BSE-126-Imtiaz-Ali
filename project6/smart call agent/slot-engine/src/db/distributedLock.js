const { createClient } = require('redis');
const crypto = require('crypto');
const config = require('../config/env');

const client = createClient({ url: config.REDIS_URL });
client.on('error', (err) => console.error('Redis lock client error', err));
client.connect();

// Lua script for safe release: only delete the key if it still holds the
// token we set (prevents accidentally releasing a lock some other process
// has since acquired after our own lock expired).
const RELEASE_SCRIPT = `
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
`;

/**
 * Acquires a short-lived distributed lock on `resourceKey`. This is the
 * first line of defense against two callers racing for the same slot when
 * capacity is down to 1 — it serializes concurrent requests *before* they
 * even reach the database, so the Postgres row-level lock (SELECT ... FOR
 * UPDATE in reservation/holdSlot.js) is a second, belt-and-suspenders
 * guarantee rather than the only one.
 */
async function acquireLock(resourceKey, ttlMs = 5000) {
  const token = crypto.randomUUID();
  const key = `lock:slot:${resourceKey}`;

  const result = await client.set(key, token, { NX: true, PX: ttlMs });
  if (result !== 'OK') return null;

  return {
    release: async () => {
      await client.eval(RELEASE_SCRIPT, { keys: [key], arguments: [token] });
    },
  };
}

/**
 * Retries acquisition briefly (a caller losing the race should get a fast,
 * clear "try a different slot" response, not hang) before giving up.
 */
async function withSlotLock(resourceKey, fn, { retries = 5, retryDelayMs = 100 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const lock = await acquireLock(resourceKey);
    if (lock) {
      try {
        return await fn();
      } finally {
        await lock.release();
      }
    }
    await new Promise((r) => setTimeout(r, retryDelayMs));
  }
  throw new Error('SLOT_LOCK_CONTENDED'); // caller should surface as "try another slot"
}

module.exports = { acquireLock, withSlotLock };
