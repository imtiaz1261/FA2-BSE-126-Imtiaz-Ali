/**
 * Formats a tracking number for clear spoken read-back:
 *  - Prefix letters are spelled out individually (TTS engines pronounce
 *    single capital letters as letter names naturally).
 *  - Year, sequence, and check digit are read digit-by-digit, grouped in
 *    chunks of 3 with a pause (comma) between groups — easier to catch on
 *    a phone line and easier to write down than one long number.
 *
 * Two outputs are provided:
 *  - `ssmlText` — literal spoken-word text (e.g. "zero zero four") for TTS
 *    engines that read digits as full words more reliably than digit
 *    glyphs on a phone connection.
 *  - `displayGrouped` — the same grouping as plain digits (e.g. "004-821-7")
 *    for use in the SMS/receipt text.
 */

const DIGIT_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];

function digitsToWords(digitString) {
  return digitString.split('').map((d) => DIGIT_WORDS[Number(d)]);
}

/** Groups a digit string into chunks of `size`, left to right. */
function chunkDigits(digitString, size = 3) {
  const chunks = [];
  for (let i = 0; i < digitString.length; i += size) {
    chunks.push(digitString.slice(i, i + size));
  }
  return chunks;
}

function spellPrefixLetters(prefix) {
  return prefix.split('').join(', ');
}

/**
 * Builds the full spoken read-back string for a tracking number like
 * "IDR-2026-004821-7":
 *   "I, D, R -- two zero two six -- zero zero four, eight two one, seven"
 */
function formatForReadback(trackingNumber) {
  const [prefix, year, sequence, checkDigit] = trackingNumber.split('-');
  if (!prefix || !year || !sequence || !checkDigit) {
    throw new Error(`Cannot format malformed tracking number for readback: ${trackingNumber}`);
  }

  const spokenPrefix = spellPrefixLetters(prefix);
  const spokenYear = digitsToWords(year).join(' ');

  const sequenceAndCheck = `${sequence}${checkDigit}`; // 7 digits total
  const groups = chunkDigits(sequenceAndCheck, 3);
  const spokenGroups = groups.map((g) => digitsToWords(g).join(' ')).join(', ');

  return {
    spokenText: `${spokenPrefix} -- ${spokenYear} -- ${spokenGroups}`,
    displayGrouped: `${prefix}-${year}-${groups.join('-')}`,
  };
}

module.exports = { formatForReadback, chunkDigits, digitsToWords };
