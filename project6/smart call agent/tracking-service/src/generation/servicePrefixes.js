/**
 * Explicit mapping from service_id (Module 4's catalog) to a fixed 3-letter
 * tracking-number prefix. Kept as a maintained lookup table rather than
 * auto-derived from service_id initials, since auto-derivation risks
 * collisions as new services are added (e.g. both "passport_new" and
 * "passport_renewal" would otherwise both derive to "PN"/"PR"-ish
 * ambiguity) — a human should assign new prefixes deliberately when a new
 * service is added to the catalog.
 */
const SERVICE_PREFIXES = {
  id_card_renewal: 'IDR',
  new_id_card: 'NID',
  passport_new: 'PPN',
  passport_renewal: 'PPR',
  child_registration: 'CHR',
};

function getPrefixForService(serviceId) {
  const prefix = SERVICE_PREFIXES[serviceId];
  if (!prefix) {
    throw new Error(`No tracking-number prefix configured for service_id "${serviceId}". Add one to SERVICE_PREFIXES.`);
  }
  return prefix;
}

module.exports = { SERVICE_PREFIXES, getPrefixForService };
