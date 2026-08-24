/**
 * Service catalog data model:
 *   {
 *     service_id: string,             // stable slug, e.g. "id_card_renewal"
 *     name: string,                   // display name
 *     description: string,            // short human-readable description
 *     required_documents: string[],   // read aloud / texted to the caller
 *     avg_duration_minutes: number,   // used by the Slot Engine (Module 5) for scheduling
 *     eligible_locations: string[],   // location/counter IDs that can serve this service
 *     example_phrases: string[],      // anchors used in the classifier prompt (not exhaustive)
 *     active: boolean,
 *   }
 */

function validateServiceEntry(entry) {
  const errors = [];
  if (!entry.service_id || typeof entry.service_id !== 'string') {
    errors.push('service_id is required and must be a string');
  }
  if (!entry.name) errors.push('name is required');
  if (!entry.description) errors.push('description is required');
  if (!Array.isArray(entry.required_documents) || entry.required_documents.length === 0) {
    errors.push('required_documents must be a non-empty array');
  }
  if (!Number.isInteger(entry.avg_duration_minutes) || entry.avg_duration_minutes <= 0) {
    errors.push('avg_duration_minutes must be a positive integer');
  }
  if (!Array.isArray(entry.eligible_locations) || entry.eligible_locations.length === 0) {
    errors.push('eligible_locations must be a non-empty array');
  }
  return { valid: errors.length === 0, errors };
}

const SEED_SERVICES = [
  {
    service_id: 'id_card_renewal',
    name: 'ID Card Renewal',
    description: 'Renewal of an existing, expired, or soon-to-expire national ID card.',
    required_documents: [
      'Existing/expired ID card (original)',
      'One recent passport-size photograph',
      'Proof of current address (utility bill, within 3 months)',
    ],
    avg_duration_minutes: 15,
    eligible_locations: ['counter_1', 'counter_2', 'counter_3'],
    example_phrases: [
      'my id card is expiring',
      'renew my id card',
      'id card renewal',
      'purani id card',
      'card ki renewal karwani hai',
    ],
    active: true,
  },
  {
    service_id: 'new_id_card',
    name: 'New ID Card',
    description: 'First-time issuance of a national ID card for a citizen who does not have one.',
    required_documents: [
      'Birth certificate (original)',
      'Parent/guardian ID card (original + copy), if applicant is a minor',
      'Two recent passport-size photographs',
      'Proof of current address',
    ],
    avg_duration_minutes: 25,
    eligible_locations: ['counter_1', 'counter_2'],
    example_phrases: [
      'i need a new id card',
      'i dont have an id card yet',
      'first time id card',
      'naya id card banwana hai',
      'mera pehli baar id card',
    ],
    active: true,
  },
  {
    service_id: 'passport_new',
    name: 'Passport - New',
    description: 'First-time passport application for a citizen who has never held a passport.',
    required_documents: [
      'National ID card (original + copy)',
      'Birth certificate (original)',
      'Two recent passport-size photographs (white background)',
      'Proof of address',
    ],
    avg_duration_minutes: 30,
    eligible_locations: ['counter_3', 'counter_4'],
    example_phrases: [
      'new passport',
      'i need a passport for the first time',
      'naya passport banwana hai',
      'never had a passport before',
    ],
    active: true,
  },
  {
    service_id: 'passport_renewal',
    name: 'Passport - Renewal',
    description: 'Renewal of an existing passport that is expired or nearing expiry.',
    required_documents: [
      'Existing/expired passport (original)',
      'National ID card (original + copy)',
      'Two recent passport-size photographs (white background)',
    ],
    avg_duration_minutes: 20,
    eligible_locations: ['counter_3', 'counter_4'],
    example_phrases: [
      'renew my passport',
      'my passport is expiring',
      'passport ki renewal',
      'purana passport renew karwana hai',
    ],
    active: true,
  },
  {
    service_id: 'child_registration',
    name: 'Child Registration',
    description: 'Registration of a newborn or minor child in the national civil registry, including birth certificate issuance.',
    required_documents: [
      'Hospital birth notification / discharge slip',
      'Both parents\u2019 ID cards (original + copy)',
      'Marriage certificate of parents (if available)',
    ],
    avg_duration_minutes: 20,
    eligible_locations: ['counter_1', 'counter_5'],
    example_phrases: [
      'register my child',
      'newborn registration',
      'bachay ka registration karwana hai',
      'birth certificate for my baby',
    ],
    active: true,
  },
];

module.exports = { validateServiceEntry, SEED_SERVICES };
