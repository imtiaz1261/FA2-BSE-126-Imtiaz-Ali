const { computeCheckDigit } = require('../checksum/checkDigit');
const { SERVICE_PREFIXES } = require('../generation/servicePrefixes');

const TRACKING_NUMBER_PATTERN = /^([A-Z]{3})-(\d{4})-(\d{6})-(\d)$/;

const KNOWN_PREFIXES = new Set(Object.values(SERVICE_PREFIXES));

/**
 * Validates a tracking number's format and check digit WITHOUT touching
 * the database — this is the fast-fail step a status-check form (Module 9)
 * or the dialogue manager should run first, so an obvious typo ("looks
 * like a digit is off") gets a clear, instant response instead of a
 * generic "not found" after a wasted DB round trip.
 *
 * Returns { valid: true, parsed: {...} } or
 *         { valid: false, reason: 'bad_format' | 'unknown_prefix' | 'checksum_mismatch' }
 */
function validateTrackingNumber(rawInput) {
  if (!rawInput || typeof rawInput !== 'string') {
    return { valid: false, reason: 'bad_format' };
  }

  // Be forgiving of how a caller might type/say it: normalize whitespace,
  // straighten curly hyphens, and uppercase before matching the strict
  // pattern.
  const normalized = rawInput.trim().toUpperCase().replace(/[\s]+/g, '').replace(/[–—]/g, '-');

  const match = TRACKING_NUMBER_PATTERN.exec(normalized);
  if (!match) {
    return { valid: false, reason: 'bad_format' };
  }

  const [, prefix, year, sequence, checkDigitStr] = match;

  if (!KNOWN_PREFIXES.has(prefix)) {
    return { valid: false, reason: 'unknown_prefix' };
  }

  const expectedCheckDigit = computeCheckDigit({ prefix, year, sequence });
  const actualCheckDigit = Number(checkDigitStr);

  if (expectedCheckDigit !== actualCheckDigit) {
    return { valid: false, reason: 'checksum_mismatch' };
  }

  return {
    valid: true,
    parsed: { prefix, year: Number(year), sequence, checkDigit: actualCheckDigit, normalized },
  };
}

module.exports = { validateTrackingNumber, TRACKING_NUMBER_PATTERN };
