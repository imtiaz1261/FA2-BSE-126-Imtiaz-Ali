require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 5000,
  DATABASE_URL: required('DATABASE_URL'),

  ANTHROPIC_API_KEY: required('ANTHROPIC_API_KEY'),
  CLASSIFICATION_MODEL: process.env.CLASSIFICATION_MODEL || 'claude-sonnet-4-6',

  // Below this confidence, treat the top match as uncertain and ask a
  // clarifying question instead of committing to a service_id.
  CONFIDENCE_THRESHOLD: parseFloat(process.env.CONFIDENCE_THRESHOLD || '0.75'),

  // If the top two candidate services are within this margin of each other,
  // treat it as ambiguous even if the top score alone clears the threshold
  // (e.g. "ID card" alone could mean renewal or new — both may score high).
  AMBIGUITY_MARGIN: parseFloat(process.env.AMBIGUITY_MARGIN || '0.15'),
};
