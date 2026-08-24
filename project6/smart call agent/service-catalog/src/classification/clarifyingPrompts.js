/**
 * Clarifying-question templates, keyed by which pair/group of services is
 * ambiguous. Falls back to a generic template if no specific pairing is
 * defined. Kept as templates (not LLM-generated per-call) so the exact
 * wording is predictable, reviewable, and fast — no extra LLM round trip
 * just to phrase a question we already know the shape of.
 */

const SPECIFIC_CLARIFICATIONS = {
  'id_card_renewal|new_id_card': {
    en: 'Just to confirm — is this to renew an ID card you already have, or to get a brand new one for the first time?',
    ur: 'Sirf tasdeeq ke liye — kya yeh apni maujooda ID card ki renewal ke liye hai, ya bilkul nayi ID card banwane ke liye?',
  },
  'passport_new|passport_renewal': {
    en: 'Is this for a completely new passport, or to renew a passport you already hold?',
    ur: 'Kya yeh bilkul naye passport ke liye hai, ya aapke maujooda passport ki renewal ke liye?',
  },
};

const GENERIC_CLARIFICATION = {
  en: (candidateNames) =>
    `I want to make sure I get this right — is this for ${candidateNames.join(' or ')}?`,
  ur: (candidateNames) =>
    `Main yeh yaqeeni banana chahta hoon — kya yeh ${candidateNames.join(' ya ')} ke liye hai?`,
};

function buildClarifyingQuestion({ candidates, language }) {
  const ids = candidates.map((c) => c.service_id).sort();
  const key = ids.join('|');

  if (SPECIFIC_CLARIFICATIONS[key]) {
    return SPECIFIC_CLARIFICATIONS[key][language] || SPECIFIC_CLARIFICATIONS[key].en;
  }

  const names = candidates.map((c) => c.name);
  const template = GENERIC_CLARIFICATION[language] || GENERIC_CLARIFICATION.en;
  return template(names);
}

module.exports = { buildClarifyingQuestion };
