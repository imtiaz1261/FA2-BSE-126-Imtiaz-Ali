const config = require('../config/env');
const { getSession, incrementRetries } = require('./sessionStore');

/**
 * Called by the media-stream bridge whenever the voice agent returns a
 * parsed transcript/intent for a turn. Decides whether this call should
 * be escalated to a human agent.
 *
 * Escalation triggers:
 *  1. Caller explicitly says a trigger phrase ("talk to a person", etc.)
 *  2. The voice agent fails to parse an intent after MAX_NO_RESPONSE_RETRIES
 *     consecutive turns (caller is stuck / agent is confused)
 *  3. The voice-agent backend itself errors or times out (network/model failure)
 */
async function shouldEscalateToHuman({ callSid, transcript, agentParsedOk, agentError }) {
  if (agentError) {
    return { escalate: true, reason: 'agent_error' };
  }

  const lowerTranscript = (transcript || '').toLowerCase();
  const matchedPhrase = config.HUMAN_TRANSFER_TRIGGER_PHRASES.find((phrase) =>
    lowerTranscript.includes(phrase)
  );
  if (matchedPhrase) {
    return { escalate: true, reason: 'caller_requested', matchedPhrase };
  }

  if (!agentParsedOk) {
    const session = await incrementRetries(callSid);
    if (session.retries >= config.MAX_NO_RESPONSE_RETRIES) {
      return { escalate: true, reason: 'max_retries_exceeded' };
    }
  }

  return { escalate: false };
}

/**
 * Builds the whisper/context summary read to the human agent (or shown on
 * their softphone screen-pop) so the caller never has to repeat themselves.
 */
async function buildHandoffContext(callSid) {
  const session = await getSession(callSid);
  return {
    callSid,
    callerNumber: session?.from || 'unknown',
    purposeSoFar: session?.purposeSoFar || 'not yet captured',
    retries: session?.retries || 0,
    reason: session?.escalationReason || 'unspecified',
  };
}

module.exports = { shouldEscalateToHuman, buildHandoffContext };
