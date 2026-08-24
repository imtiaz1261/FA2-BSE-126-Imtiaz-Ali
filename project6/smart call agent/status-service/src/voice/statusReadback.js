const { STATUSES } = require('../status/statusModel');

/**
 * Spoken description per status, in each supported language. Template-based
 * (not LLM-generated) for the same reason as the booking readback (Module
 * 6) — status is exactly the kind of fact that must never be paraphrased
 * loosely.
 */
const STATUS_DESCRIPTIONS = {
  [STATUSES.BOOKED]: {
    en: 'Your appointment is booked and confirmed.',
    ur: 'Aapki appointment book aur confirm ho chuki hai.',
  },
  [STATUSES.CHECKED_IN]: {
    en: 'You have checked in at the service center.',
    ur: 'Aap service center par check-in kar chuke hain.',
  },
  [STATUSES.DOCUMENTS_VERIFIED]: {
    en: 'Your documents have been verified.',
    ur: 'Aapke documents verify ho chuke hain.',
  },
  [STATUSES.PROCESSING]: {
    en: 'Your application is currently being processed.',
    ur: 'Aapki application abhi process ho rahi hai.',
  },
  [STATUSES.READY_FOR_COLLECTION]: {
    en: 'Good news — your application is ready for collection.',
    ur: 'Khush khabri — aapki application collection ke liye tayyar hai.',
  },
  [STATUSES.COMPLETED]: {
    en: 'Your application has been completed.',
    ur: 'Aapki application mukammal ho chuki hai.',
  },
  [STATUSES.CANCELLED]: {
    en: 'This appointment has been cancelled.',
    ur: 'Yeh appointment cancel kar di gayi hai.',
  },
};

/**
 * Called by the Voice Agent's dialogue manager (Module 3) in a
 * "check-status" flow: caller says "check my application status", provides
 * their tracking number (spoken, extracted the same way slot-filling
 * extracts other fields — see prompts.js's pattern — or via DTMF keypad
 * entry captured by the telephony gateway and forwarded as digits), the
 * dialogue manager calls GET /status/:trackingNumber?phone=<caller ID from
 * session>, and speaks this text.
 */
function buildStatusReadback({ trackingNumber, currentStatus, language = 'en' }) {
  const description =
    (STATUS_DESCRIPTIONS[currentStatus] && STATUS_DESCRIPTIONS[currentStatus][language]) ||
    STATUS_DESCRIPTIONS[currentStatus]?.en ||
    (language === 'ur' ? 'Status maloom nahi ho saka.' : 'Status could not be determined.');

  const intro =
    language === 'ur'
      ? `Aapke tracking number ${trackingNumber} ke liye:`
      : `For tracking number ${trackingNumber}:`;

  return `${intro} ${description}`;
}

module.exports = { buildStatusReadback, STATUS_DESCRIPTIONS };
