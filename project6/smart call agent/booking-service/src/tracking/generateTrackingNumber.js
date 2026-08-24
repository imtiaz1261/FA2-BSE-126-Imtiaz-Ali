const crypto = require('crypto');

/**
 * Lightweight tracking-number generator used inside the atomic confirmation
 * transaction (Module 7 formalizes this further — dedicated prefixing
 * rules per service, checksum digit, etc. — but the collision-safe
 * generate-and-retry pattern here is what Module 7 will build on, not
 * replace).
 *
 * Format: <SERVICE_PREFIX>-<YYYYMMDD>-<5-char base36>
 * e.g. IDR-20260815-4F7A2
 */
function serviceIdToPrefix(serviceId) {
  const parts = serviceId.split('_');
  const letters = parts.map((p) => p[0]).join('').toUpperCase();
  return letters.slice(0, 4) || 'SVC';
}

function generateTrackingNumber(serviceId, date) {
  const prefix = serviceIdToPrefix(serviceId);
  const dateStr = date.replace(/-/g, '');
  const random = crypto.randomBytes(4).toString('hex').slice(0, 5).toUpperCase();
  return `${prefix}-${dateStr}-${random}`;
}

module.exports = { generateTrackingNumber };
