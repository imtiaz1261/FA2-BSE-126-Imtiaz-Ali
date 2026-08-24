require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 8500,

  // Same shared Postgres instance as the other services — see Module 6's
  // README for why. Never hardcoded here; comes from the environment.
  DATABASE_URL: required('DATABASE_URL'),
};
