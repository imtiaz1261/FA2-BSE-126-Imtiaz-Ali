/**
 * Check-digit algorithm for tracking numbers.
 *
 * The Luhn algorithm is defined over digit strings, but our payload
 * (SERVICE-PREFIX + YEAR + SEQUENCE) includes letters. We fold the letters
 * into digits first, then run standard Luhn over the resulting numeric
 * string — this way a typo anywhere in the number, including the prefix
 * letters, changes the payload and is caught by the check digit, not just
 * a typo in the numeric portion.
 *
 * Letter -> digit folding: A=01 .. Z=26 (two digits per letter), so "IDR"
 * becomes "09" + "04" + "18" = "090418". This is a standard, reversible,
 * simple encoding — not cryptographic, just enough structure for the
 * checksum to be sensitive to every character typed.
 */

function letterToTwoDigits(letter) {
  const code = letter.toUpperCase().charCodeAt(0) - 64; // 'A' -> 1
  if (code < 1 || code > 26) {
    throw new Error(`Not an A-Z letter: ${letter}`);
  }
  return String(code).padStart(2, '0');
}

function foldPrefixToDigits(prefix) {
  return prefix
    .split('')
    .map(letterToTwoDigits)
    .join('');
}

/**
 * Standard Luhn check-digit computation over a numeric payload string.
 * Doubles every second digit counting from the rightmost payload digit
 * (since the check digit itself will be appended after and is never
 * doubled), per the standard algorithm.
 */
function computeLuhnCheckDigit(numericPayload) {
  if (!/^\d+$/.test(numericPayload)) {
    throw new Error('computeLuhnCheckDigit expects a digit-only string');
  }

  let sum = 0;
  let shouldDouble = true;
  for (let i = numericPayload.length - 1; i >= 0; i--) {
    let digit = Number(numericPayload[i]);
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return (10 - (sum % 10)) % 10;
}

/**
 * Builds the numeric payload from the three human-readable components and
 * returns the single check digit (0-9) for a NEW tracking number, or to
 * verify an EXISTING one (recompute and compare).
 */
function computeCheckDigit({ prefix, year, sequence }) {
  const numericPayload = `${foldPrefixToDigits(prefix)}${year}${sequence}`;
  return computeLuhnCheckDigit(numericPayload);
}

module.exports = { computeCheckDigit, foldPrefixToDigits, computeLuhnCheckDigit, letterToTwoDigits };
