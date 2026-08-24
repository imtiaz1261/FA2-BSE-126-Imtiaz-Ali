const twilio = require('twilio');
const config = require('../config/env');

const client = twilio(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN);

/**
 * Starts recording on an already-in-progress call. Use this instead of the
 * <Record> TwiML verb if you need to start recording programmatically
 * (e.g. only after the consent notice finishes and the caller has not
 * opted out), or want finer control over pause/resume around sensitive
 * moments in the conversation (e.g. if payment/PII capture is ever added).
 */
async function startRecording(callSid) {
  return client.calls(callSid).recordings.create({
    recordingStatusCallback: '/voice/recording-status',
    recordingStatusCallbackEvent: ['in-progress', 'completed'],
  });
}

async function pauseRecording(callSid, recordingSid) {
  return client.calls(callSid).recordings(recordingSid).update({ status: 'paused' });
}

async function resumeRecording(callSid, recordingSid) {
  return client.calls(callSid).recordings(recordingSid).update({ status: 'in-progress' });
}

async function stopRecording(callSid, recordingSid) {
  return client.calls(callSid).recordings(recordingSid).update({ status: 'stopped' });
}

module.exports = { startRecording, pauseRecording, resumeRecording, stopRecording };
