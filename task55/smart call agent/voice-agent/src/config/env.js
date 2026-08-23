require('dotenv').config();

function required(name) {
  const val = process.env[name];
  if (!val) throw new Error(`Missing required env var: ${name}`);
  return val;
}

module.exports = {
  PORT: process.env.PORT || 4000,

  // STT provider (streaming, low-latency)
  STT_PROVIDER: process.env.STT_PROVIDER || 'deepgram',
  STT_API_KEY: required('STT_API_KEY'),
  STT_LANGUAGES: ['en', 'ur'], // English + Urdu; extend as needed

  // TTS provider (streaming, natural-sounding, per-language voices)
  TTS_PROVIDER: process.env.TTS_PROVIDER || 'azure',
  TTS_API_KEY: required('TTS_API_KEY'),
  TTS_VOICES: {
    en: process.env.TTS_VOICE_EN || 'en-US-JennyNeural',
    ur: process.env.TTS_VOICE_UR || 'ur-PK-UzmaNeural',
  },

  // LLM dialogue manager
  ANTHROPIC_API_KEY: required('ANTHROPIC_API_KEY'),
  DIALOGUE_MODEL: process.env.DIALOGUE_MODEL || 'claude-sonnet-4-6',

  // Downstream services this agent calls as tools
  SLOT_ENGINE_BASE_URL: required('SLOT_ENGINE_BASE_URL'),
  BOOKING_SERVICE_BASE_URL: required('BOOKING_SERVICE_BASE_URL'),

  // Latency budget (Module 3 target: sub-1.5s end-to-end per turn)
  LATENCY_BUDGET_MS: 1500,
  STT_FINAL_SILENCE_MS: 500, // how long to wait after speech stops before treating an utterance as "final"
  BARGE_IN_MIN_SPEECH_MS: 200, // caller speech duration before we treat it as a real interruption, not noise

  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',
};
