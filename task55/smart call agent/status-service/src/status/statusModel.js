/**
 * Status lifecycle:
 *   Booked -> CheckedIn -> DocumentsVerified -> Processing
 *          -> ReadyForCollection -> Completed
 * Cancelled is reachable from any non-terminal state.
 */
const STATUSES = Object.freeze({
  BOOKED: 'Booked',
  CHECKED_IN: 'CheckedIn',
  DOCUMENTS_VERIFIED: 'DocumentsVerified',
  PROCESSING: 'Processing',
  READY_FOR_COLLECTION: 'ReadyForCollection',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
});

const TERMINAL_STATUSES = new Set([STATUSES.COMPLETED, STATUSES.CANCELLED]);

// Forward progression order — used to validate that a staff update moves
// the status forward (or to Cancelled), never backward by mistake.
const PROGRESSION_ORDER = [
  STATUSES.BOOKED,
  STATUSES.CHECKED_IN,
  STATUSES.DOCUMENTS_VERIFIED,
  STATUSES.PROCESSING,
  STATUSES.READY_FOR_COLLECTION,
  STATUSES.COMPLETED,
];

/**
 * Statuses that are citizen-relevant milestones worth a proactive SMS — per
 * the design brief, specifically ReadyForCollection and Completed.
 * Intermediate internal stages (CheckedIn, DocumentsVerified, Processing)
 * are tracked and visible on lookup, but don't push a notification —
 * pushing on every internal step would train citizens to ignore the SMS
 * channel.
 */
const NOTIFY_ON_STATUSES = new Set([STATUSES.READY_FOR_COLLECTION, STATUSES.COMPLETED]);

function isValidStatus(status) {
  return Object.values(STATUSES).includes(status);
}

/**
 * Validates a proposed transition. Returns { valid: true } or
 * { valid: false, reason }.
 */
function validateTransition(fromStatus, toStatus) {
  if (!isValidStatus(toStatus)) {
    return { valid: false, reason: 'unknown_status' };
  }

  if (TERMINAL_STATUSES.has(fromStatus)) {
    return { valid: false, reason: 'already_terminal' };
  }

  if (toStatus === STATUSES.CANCELLED) {
    return { valid: true }; // cancellable from any non-terminal state
  }

  const fromIndex = PROGRESSION_ORDER.indexOf(fromStatus);
  const toIndex = PROGRESSION_ORDER.indexOf(toStatus);

  if (fromIndex === -1 || toIndex === -1) {
    return { valid: false, reason: 'unknown_status' };
  }
  if (toIndex <= fromIndex) {
    return { valid: false, reason: 'backward_or_no_op_transition' };
  }
  // Allow skipping stages (e.g. Booked -> Processing directly) since real
  // counter workflows don't always hit every intermediate stage, but never
  // allow moving backward.
  return { valid: true };
}

module.exports = {
  STATUSES,
  TERMINAL_STATUSES,
  PROGRESSION_ORDER,
  NOTIFY_ON_STATUSES,
  isValidStatus,
  validateTransition,
};
