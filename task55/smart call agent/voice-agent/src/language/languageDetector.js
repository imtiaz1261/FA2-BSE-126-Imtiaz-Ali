/**
 * Detects the caller's language from their very first STT transcript so the
 * whole call (TTS voice + LLM dialogue prompts) can continue in that
 * language. Two-stage approach for speed + accuracy:
 *
 *  1. Fast heuristic: Urdu script (Arabic-range Unicode) is unambiguous.
 *  2. Romanized fallback: many callers speak Urdu but the STT engine may
 *     transcribe it phonetically in Latin script ("mujhe passport banwana
 *     hai"). A small keyword/n-gram check catches the common case without
 *     an extra network round trip; only fall through to the LLM classifier
 *     (used already for turn 1's intent extraction, so no added latency)
 *     when neither heuristic is confident.
 */

const URDU_UNICODE_RANGE = /[\u0600-\u06FF\u0750-\u077F]/;

// Small set of very common Roman-Urdu function words/greetings. Not
// exhaustive by design — this only needs to break ties fast; the LLM call
// that follows (for intent/slot extraction) double-checks language as part
// of its structured output and can override this guess.
const ROMAN_URDU_MARKERS = [
  'mujhe', 'mera', 'meri', 'hai', 'chahiye', 'kar', 'banwana', 'karwana',
  'assalam', 'salam', 'kal', 'aaj', 'waqt', 'tareekh',
];

function detectLanguageFromText(text) {
  if (!text || !text.trim()) return { language: 'unknown', confidence: 0 };

  if (URDU_UNICODE_RANGE.test(text)) {
    return { language: 'ur', confidence: 0.99, method: 'script' };
  }

  const lower = text.toLowerCase();
  const hits = ROMAN_URDU_MARKERS.filter((w) => lower.includes(w)).length;
  if (hits >= 2) {
    return { language: 'ur', confidence: 0.7, method: 'roman-urdu-heuristic' };
  }
  if (hits === 1) {
    return { language: 'ur', confidence: 0.5, method: 'roman-urdu-heuristic-weak' };
  }

  // Default: assume English unless the LLM classification step (which sees
  // full sentence structure, not just keywords) says otherwise.
  return { language: 'en', confidence: 0.6, method: 'default-english' };
}

/**
 * Called once per call, right after the first final STT transcript arrives.
 * If confidence is low, the dialogue manager's first LLM call also includes
 * a `detected_language` field in its structured output (see
 * dialogue/prompts.js) which takes precedence once available.
 */
function resolveInitialLanguage(firstTranscript) {
  const guess = detectLanguageFromText(firstTranscript);
  return guess.confidence >= 0.7 ? guess.language : 'en'; // safe default while LLM confirms
}

module.exports = { detectLanguageFromText, resolveInitialLanguage };
