/**
 * Location display details for receipts and letterhead-style headers.
 * Kept as a small maintained lookup (mirrors service-catalog's
 * service-prefix pattern) rather than inferred from location_id — an
 * admin should set the printable name/address deliberately when a new
 * counter/branch is added. In a fuller build this table would move into
 * the Admin Console (Module 11) as an editable resource; kept static here
 * to keep this module's scope focused on receipt generation itself.
 */
const LOCATION_DIRECTORY = {
  counter_1: { name: 'Citizen Services Center — Main Branch', address: 'Plot 12, G-8 Markaz, Islamabad' },
  counter_2: { name: 'Citizen Services Center — Main Branch', address: 'Plot 12, G-8 Markaz, Islamabad' },
  counter_3: { name: 'Citizen Services Center — Passport Wing', address: 'Plot 12, G-8 Markaz, Islamabad' },
  counter_4: { name: 'Citizen Services Center — Passport Wing', address: 'Plot 12, G-8 Markaz, Islamabad' },
  counter_5: { name: 'Citizen Services Center — Family Registration Wing', address: 'Plot 12, G-8 Markaz, Islamabad' },
};

function getLocationDetails(locationId) {
  return (
    LOCATION_DIRECTORY[locationId] || {
      name: 'Citizen Services Center',
      address: 'Address on file',
    }
  );
}

module.exports = { getLocationDetails, LOCATION_DIRECTORY };
