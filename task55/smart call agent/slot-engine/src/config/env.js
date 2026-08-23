require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 6000,

  // Never hardcode credentials here — DATABASE_URL (including its password)
  // is injected via the environment (.env locally, secrets manager in
  // production). See .env.example for the expected shape.
  DATABASE_URL: required('DATABASE_URL'),
  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',

  // Hold TTL: matches the "expires after 2 minutes if not confirmed" spec.
  HOLD_TTL_SECONDS: parseInt(process.env.HOLD_TTL_SECONDS || '120', 10),

  // How often the background sweeper looks for expired holds to release.
  HOLD_SWEEP_INTERVAL_MS: parseInt(process.env.HOLD_SWEEP_INTERVAL_MS || '15000', 10),

  // Business-hours slot generation defaults (used by scripts/generateSlots.js)
  DEFAULT_DAY_START: process.env.DEFAULT_DAY_START || '09:00',
  DEFAULT_DAY_END: process.env.DEFAULT_DAY_END || '17:00',
  DEFAULT_BLOCK_MINUTES: parseInt(process.env.DEFAULT_BLOCK_MINUTES || '30', 10),
  DEFAULT_CAPACITY_PER_BLOCK: parseInt(process.env.DEFAULT_CAPACITY_PER_BLOCK || '4', 10),

  // Nearest-alternative search window for GET /availability
  NEAREST_SEARCH_DAYS: parseInt(process.env.NEAREST_SEARCH_DAYS || '3', 10),
  NEAREST_RESULTS_LIMIT: parseInt(process.env.NEAREST_RESULTS_LIMIT || '5', 10),
};
