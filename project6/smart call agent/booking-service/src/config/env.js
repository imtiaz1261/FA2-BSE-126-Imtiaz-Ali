require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 7000,

  // Same physical Postgres instance/schema as slot-engine (see README
  // section "Why this service touches the slots tables directly") — never
  // hardcode the password here, it comes from the environment.
  DATABASE_URL: required('DATABASE_URL'),

  SLOT_ENGINE_BASE_URL: required('SLOT_ENGINE_BASE_URL'), // used for hold/release, not for the atomic confirm
  NOTIFICATION_SERVICE_BASE_URL: required('NOTIFICATION_SERVICE_BASE_URL'), // Module 10

  TRACKING_NUMBER_MAX_RETRIES: 5,
};
