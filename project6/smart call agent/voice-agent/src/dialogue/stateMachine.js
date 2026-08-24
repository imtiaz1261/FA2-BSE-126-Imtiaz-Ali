/**
 * Slot-filling state machine — mirrors the call-session state machine from
 * Module 1 (Greeting -> PurposeCapture -> SlotSearch -> DateTimeNegotiation
 * -> Confirmation -> Completed), specialized here for the three required
 * slots: purpose_of_visit, preferred_day, preferred_time.
 *
 * The LLM never free-forms the flow — it fills one slot at a time, and each
 * captured slot is echoed back to the caller for confirmation before moving
 * on (per the design brief: "confirm each captured slot back to the caller
 * before moving on").
 */

const STATES = Object.freeze({
  GREETING: 'GREETING',
  CAPTURING_PURPOSE: 'CAPTURING_PURPOSE',
  CONFIRMING_PURPOSE: 'CONFIRMING_PURPOSE',
  CHECKING_SLOTS: 'CHECKING_SLOTS',
  CAPTURING_DAY: 'CAPTURING_DAY',
  CAPTURING_TIME: 'CAPTURING_TIME',
  CONFIRMING_DATETIME: 'CONFIRMING_DATETIME',
  FINAL_CONFIRMATION: 'FINAL_CONFIRMATION',
  COMPLETED: 'COMPLETED',
  TRANSFERRED: 'TRANSFERRED',
  ABANDONED: 'ABANDONED',
});

const REQUIRED_SLOTS = ['purpose_of_visit', 'preferred_day', 'preferred_time'];

function initialDialogueState() {
  return {
    state: STATES.GREETING,
    language: 'en',
    slots: {
      purpose_of_visit: null,
      preferred_day: null,
      preferred_time: null,
    },
    confirmed: {
      purpose_of_visit: false,
      preferred_day: false,
      preferred_time: false,
    },
    availableSlotsCache: null, // result of the last Slot Engine query
    clarificationAttempts: 0,
    turnHistory: [], // last N turns, for LLM context window management
  };
}

/**
 * Given the current dialogue state and the LLM's structured output for this
 * turn, compute the next state. Keeping this transition logic outside the
 * LLM (rather than trusting it to "decide" the next state itself) is what
 * makes the flow reliable and testable — the LLM's only job is extraction
 * and natural phrasing, not flow control.
 */
function nextState(current, llmTurnOutput) {
  const { state, slots, confirmed } = current;

  switch (state) {
    case STATES.GREETING:
      return STATES.CAPTURING_PURPOSE;

    case STATES.CAPTURING_PURPOSE:
      if (llmTurnOutput.extracted.purpose_of_visit) {
        return STATES.CONFIRMING_PURPOSE;
      }
      return STATES.CAPTURING_PURPOSE; // re-ask / clarify, stay in state

    case STATES.CONFIRMING_PURPOSE:
      if (llmTurnOutput.confirmation === 'yes') {
        return STATES.CHECKING_SLOTS;
      }
      if (llmTurnOutput.confirmation === 'no') {
        return STATES.CAPTURING_PURPOSE; // caller corrected themselves
      }
      return STATES.CONFIRMING_PURPOSE;

    case STATES.CHECKING_SLOTS:
      // Transition decided by the orchestrator after the Slot Engine call
      // returns (see session/callSession.js) — either NO_SLOTS -> waitlist
      // (handled by Booking Service / Module 6) or CAPTURING_DAY.
      return STATES.CAPTURING_DAY;

    case STATES.CAPTURING_DAY:
      if (llmTurnOutput.extracted.preferred_day) {
        return STATES.CAPTURING_TIME;
      }
      return STATES.CAPTURING_DAY;

    case STATES.CAPTURING_TIME:
      if (llmTurnOutput.extracted.preferred_time) {
        return STATES.CONFIRMING_DATETIME;
      }
      return STATES.CAPTURING_TIME;

    case STATES.CONFIRMING_DATETIME:
      if (llmTurnOutput.confirmation === 'yes') {
        return STATES.FINAL_CONFIRMATION;
      }
      if (llmTurnOutput.confirmation === 'no') {
        return STATES.CAPTURING_DAY; // renegotiate day/time
      }
      return STATES.CONFIRMING_DATETIME;

    case STATES.FINAL_CONFIRMATION:
      return STATES.COMPLETED; // Booking Service (Module 6) commits here

    default:
      return state;
  }
}

function allSlotsFilled(slots) {
  return REQUIRED_SLOTS.every((key) => slots[key] !== null && slots[key] !== undefined);
}

module.exports = { STATES, REQUIRED_SLOTS, initialDialogueState, nextState, allSlotsFilled };
