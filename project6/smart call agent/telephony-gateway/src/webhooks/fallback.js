const express = require('express');
const twilio = require('twilio');
const config = require('../config/env');
const { updateSession } = require('../fallback/sessionStore');
const { buildHandoffContext } = require('../fallback/humanHandoff');

const router = express.Router();
const VoiceResponse = twilio.twiml.VoiceResponse;

// Invoked by the media-stream bridge (via a REST redirect on the live call,
// using the Twilio Calls API `update()` with a new TwiML URL) whenever
// shouldEscalateToHuman() returns true.
router.post('/transfer', async (req, res) => {
  const callSid = req.body.CallSid;
  const reason = req.query.reason || 'unspecified';

  await updateSession(callSid, { escalationReason: reason });
  const context = await buildHandoffContext(callSid);

  const twiml = new VoiceResponse();

  twiml.say(
    { voice: 'Polly.Joanna' },
    "I'm connecting you with a team member now, please hold."
  );

  // Enqueue into the human ACD/softphone queue. The queue's members
  // (staff softphones) dequeue calls and see `context` via the
  // Admin Console, which polls /api/handoff-context/:callSid.
  twiml.enqueue(
    {
      waitUrl: '/voice/queue/hold-music',
      // Whisper played only to the agent right before the call connects,
      // so staff hear the context without the caller hearing it repeated.
      waitUrlMethod: 'POST',
    },
    config.HUMAN_QUEUE_NAME
  );

  res.type('text/xml').send(twiml.toString());
  // Full structured context is also pushed to the Admin Console via
  // the Booking/Admin API so staff see it on-screen, not just heard.
  void context;
});

// Whisper TwiML played to the human agent the moment they pick up,
// summarizing what the AI agent already captured.
router.post('/agent-whisper', async (req, res) => {
  const callSid = req.query.callSid;
  const context = await buildHandoffContext(callSid);

  const twiml = new VoiceResponse();
  twiml.say(
    { voice: 'Polly.Matthew' },
    `Incoming citizen-services call. Purpose so far: ${context.purposeSoFar}. ` +
      `Reason for transfer: ${context.reason}.`
  );
  res.type('text/xml').send(twiml.toString());
});

module.exports = router;
