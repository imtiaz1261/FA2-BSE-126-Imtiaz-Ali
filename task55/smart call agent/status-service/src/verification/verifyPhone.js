/**
 * Same normalized-comparison approach as receipt-service's resend
 * verification (Module 8) — compares the last 10 digits so formatting
 * differences (spaces, dashes, a leading +, missing country code) don't
 * cause false rejections, while still requiring a real match.
 */
function normalizePhoneForComparison(phone) {
  return (phone || '').replace(/\D/g, '');
}

function phonesMatch(providedPhone, onFilePhone) {
  const provided = normalizePhoneForComparison(providedPhone);
  const onFile = normalizePhoneForComparison(onFilePhone);
  return provided.length >= 7 && provided.slice(-10) === onFile.slice(-10);
}

module.exports = { normalizePhoneForComparison, phonesMatch };
