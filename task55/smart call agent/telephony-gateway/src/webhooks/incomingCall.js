const express = require('express');
const twilio = require('twilio');
const config = require('../config/env');
const { createSession } = require('../fallback/sessionStore');
const { getQueueDepth, estimateWaitSeconds } = require('../queue/callQueue');

const router = express.Router();
const VoiceResponse = twilio.twiml.VoiceResponse;

// Twilio POSTs here the moment a citizen dials the published service number.
// This webhook URL is configured on the phone number in the Twilio Console
// (or via the Incoming Phone Numbers API): Voice -> "A call comes in" -> Webhook.
router.post('/', async (req, res) => {
  const callSid = req.body.CallSid;
  const from = req.body.From;

  // Initialize per-call session state (used later for retry counts,
  // captured purpose, and human-handoff context).
  await createSession(callSid, { from, retries: 0, purposeSoFar: null });

  const twiml = new VoiceResponse();

  // If the system is under heavy load, route straight into the human queue
  // with an estimated-wait announcement instead of starting the AI agent.
  const queueDepth = await getQueueDepth();
  const HIGH_LOAD_THRESHOLD = 25; // tune based on capacity testing
  if (queueDepth > HIGH_LOAD_THRESHOLD) {
    const waitSecs = await estimateWaitSeconds();
    twiml.say(
      { voice: 'Polly.Joanna' },
      `Thank you for calling citizen services. All lines are currently busy. ` +
        `Your estimated wait time is about ${Math.ceil(waitSecs / 60)} minutes. ` +
        `Please stay on the line.`
    );
    twiml.enqueue({ waitUrl: '/voice/queue/hold-music' }, config.HUMAN_QUEUE_NAME);
    res.type('text/xml').send(twiml.toString());
    return;
  }

  // Consent/recording notice — played before recording is armed and before
  // the AI agent starts listening, in compliance with two-party-consent rules.
  twiml.say({ voice: 'Polly.Joanna' }, config.CONSENT_NOTICE_TEXT);

  // Start call recording after the notice (see recording/recordingControl.js
  // for the REST-API alternative if you prefer starting recording via API
  // instead of TwiML, e.g. to control start/stop dynamically mid-call).
  twiml.record({
    recordingStatusCallback: '/voice/recording-status',
    recordingStatusCallbackEvent: ['in-progress', 'completed'],
    transcribe: false,
    playBeep: false,
    trim: 'do-not-trim',
  });

  // Open a real-time, bidirectional audio stream to the voice-agent backend.
  // <Connect><Stream> keeps the call live and pipes raw audio frames both ways
  // over the WebSocket at MEDIA_STREAM_WSS_URL (handled in mediaStream/bridge.js).
  const connect = twiml.connect();
  connect.stream({ url: config.MEDIA_STREAM_WSS_URL }).parameter({
    name: 'callSid',
    value: callSid,
  });

  res.type('text/xml').send(twiml.toString());
});

module.exports = router;
