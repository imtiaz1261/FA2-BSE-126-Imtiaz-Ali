/**
 * Builds the exact sentence the Voice Agent's dialogue manager speaks in
 * the CONFIRMING_DATETIME / final-readback state, before asking for
 * explicit "yes"/"confirm". Kept as a template (not LLM-generated) so the
 * readback is always precise and never paraphrases away a detail — this is
 * the one sentence in the whole call that must be exactly right.
 */

const DAY_TIME_FORMATTER = {
  en: (serviceName, date, timeBlock, locationName) =>
    `Let me confirm — that's ${serviceName} on ${date} at ${timeBlock}${
      locationName ? `, at ${locationName}` : ''
    }. Should I go ahead and book that?`,
  ur: (serviceName, date, timeBlock, locationName) =>
    `Tasdeeq kar lete hain — ${serviceName} ke liye ${date} ko ${timeBlock} baje${
      locationName ? `, ${locationName} mein` : ''
    }. Kya main yeh book kar doon?`,
};

function buildReadback({ serviceName, date, timeBlock, locationName, language = 'en' }) {
  const formatter = DAY_TIME_FORMATTER[language] || DAY_TIME_FORMATTER.en;
  return formatter(serviceName, date, timeBlock, locationName);
}

const FINAL_CONFIRMATION_TEXT = {
  en: (trackingNumber) =>
    `You're all set. Your appointment is confirmed, and your tracking number is ${trackingNumber}. ` +
    `We're sending the details to you by SMS now.`,
  ur: (trackingNumber) =>
    `Aapki appointment confirm ho gayi hai. Aapka tracking number hai ${trackingNumber}. ` +
    `Tafseelat SMS ke zariye bheji ja rahi hain.`,
};

function buildFinalConfirmation({ trackingNumber, language = 'en' }) {
  const formatter = FINAL_CONFIRMATION_TEXT[language] || FINAL_CONFIRMATION_TEXT.en;
  return formatter(trackingNumber);
}

const DECLINE_ACK_TEXT = {
  en: 'No problem, let me find another time for you.',
  ur: 'Koi baat nahi, main aapke liye doosra waqt talaash karta hoon.',
};

function buildDeclineAck({ language = 'en' }) {
  return DECLINE_ACK_TEXT[language] || DECLINE_ACK_TEXT.en;
}

module.exports = { buildReadback, buildFinalConfirmation, buildDeclineAck };
