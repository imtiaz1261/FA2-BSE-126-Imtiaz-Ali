// Centralized env/config loader. All secrets come from environment variables —
// never hardcode credentials in source.

require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 3000,

  // Twilio
  TWILIO_ACCOUNT_SID: required('TWILIO_ACCOUNT_SID'),
  TWILIO_AUTH_TOKEN: required('TWILIO_AUTH_TOKEN'),
  TWILIO_SERVICE_NUMBER: required('TWILIO_SERVICE_NUMBER'), // e.g. +9231XXXXXXX

  // This service's own publicly reachable base URL — used to build the
  // REST callback URL when redirecting a live call to the human queue
  // (mediaStream/bridge.js's redirectCallToHuman). Was previously read
  // directly via process.env without being declared/required here — fixed
  // so a missing value fails fast at startup instead of silently building
  // a broken "undefined/voice/fallback/transfer" URL mid-call.
  PUBLIC_BASE_URL: required('PUBLIC_BASE_URL'), // e.g. https://gateway.example.com (or your ngrok URL in dev)

  // Where Twilio's Media Stream should connect for real-time audio
  MEDIA_STREAM_WSS_URL: required('MEDIA_STREAM_WSS_URL'), // wss://gateway.example.com/media-stream

  // Voice-agent backend (STT->NLU->TTS service from Module 3)
  VOICE_AGENT_WS_URL: required('VOICE_AGENT_WS_URL'), // ws://voice-agent:4000/session

  // Human agent fallback
  HUMAN_QUEUE_NAME: process.env.HUMAN_QUEUE_NAME || 'citizen-services-queue',
  HUMAN_TRANSFER_TRIGGER_PHRASES: [
    'talk to a person',
    'human agent',
    'representative',
    'talk to someone',
    'real person',
    'operator',
  ],
  MAX_NO_RESPONSE_RETRIES: 2,

  // Recording consent notice (played before any recording starts)
  CONSENT_NOTICE_TEXT:
    'This call may be recorded for quality and dispute-resolution purposes. ' +
    'If you do not wish to be recorded, please say "do not record" now.',

  // Redis (call-session state, shared with voice-agent)
  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',
};
