/**
 * Minimal required caller details: full name, CNIC (if the caller has it
 * on hand — optional), and phone number. Phone defaults to the caller-ID
 * number the telephony gateway already captured (Module 2's `From` field,
 * carried in the call session), and is only asked for explicitly if the
 * caller wants appointment confirmations sent to a different number.
 */

const CNIC_PATTERN = /^\d{5}-\d{7}-\d{1}$/; // Pakistani CNIC format: 12345-1234567-1
const PHONE_PATTERN = /^\+?[0-9]{10,15}$/;

function normalizeCnic(raw) {
  if (!raw) return null;
  const digits = raw.replace(/\D/g, '');
  if (digits.length !== 13) return { valid: false, value: raw };
  const formatted = `${digits.slice(0, 5)}-${digits.slice(5, 12)}-${digits.slice(12)}`;
  return { valid: CNIC_PATTERN.test(formatted), value: formatted };
}

function normalizePhone(raw) {
  if (!raw) return { valid: false, value: null };
  const trimmed = raw.trim();
  return { valid: PHONE_PATTERN.test(trimmed), value: trimmed };
}

/**
 * Validates the caller-details payload before it's allowed into the
 * confirmation transaction. `phoneFromCallerId` is the fallback used when
 * the caller didn't explicitly provide/correct a number.
 */
function captureCallerDetails({ name, cnic, phone, phoneFromCallerId }) {
  const errors = [];

  const trimmedName = (name || '').trim();
  if (trimmedName.length < 2) {
    errors.push('name is required (at least 2 characters)');
  }

  let normalizedCnic = null;
  if (cnic) {
    const result = normalizeCnic(cnic);
    if (!result.valid) {
      errors.push('cnic does not match the expected format (12345-1234567-1)');
    } else {
      normalizedCnic = result.value;
    }
  }
  // CNIC is explicitly optional per the design brief ("if available") —
  // absence is never an error, only a malformed value is.

  const phoneToUse = phone || phoneFromCallerId;
  const phoneResult = normalizePhone(phoneToUse);
  if (!phoneResult.valid) {
    errors.push('a valid phone number is required (caller ID or explicitly provided)');
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    details: {
      name: trimmedName,
      cnic: normalizedCnic,
      phone: phoneResult.value,
    },
  };
}

module.exports = { captureCallerDetails, normalizeCnic, normalizePhone };
