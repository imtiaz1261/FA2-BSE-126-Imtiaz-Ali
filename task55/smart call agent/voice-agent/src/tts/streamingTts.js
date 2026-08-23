const fetch = require('node-fetch');
const config = require('../config/env');

/**
 * Streams synthesized speech in small chunks so the first audio reaches the
 * caller as fast as possible (important for the sub-1.5s turn budget — we
 * don't wait for the full utterance to render before starting playback).
 *
 * Reference implementation targets a generic streaming-TTS REST endpoint
 * that returns chunked mulaw/8kHz audio (matching Azure Speech's streaming
 * synthesis format), so chunks can be forwarded to Twilio's media stream
 * with no transcoding.
 *
 * Barge-in support: `synthesizeStreaming` accepts an AbortController signal.
 * The moment the STT layer emits 'speech_start' while TTS is playing, the
 * orchestrator (session/callSession.js) calls `controller.abort()`, which
 * stops the fetch stream immediately and the orchestrator stops forwarding
 * further chunks to Twilio — audio cuts off within one network round trip,
 * not at the end of the sentence.
 */
async function synthesizeStreaming({ text, language, onChunk, signal }) {
  const voice = config.TTS_VOICES[language] || config.TTS_VOICES.en;

  const res = await fetch(`https://tts.example-provider.com/v1/stream`, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.TTS_API_KEY}`,
    },
    body: JSON.stringify({
      text,
      voice,
      output_format: 'mulaw_8000hz',
      streaming: true,
    }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`TTS request failed: ${res.status}`);
  }

  for await (const chunk of res.body) {
    if (signal?.aborted) break; // barge-in: stop forwarding immediately
    onChunk(chunk.toString('base64'));
  }
}

/** Convenience wrapper the orchestrator uses so it always has an AbortController handle. */
function startInterruptibleSynthesis({ text, language, onChunk }) {
  const controller = new AbortController();
  const promise = synthesizeStreaming({ text, language, onChunk, signal: controller.signal }).catch(
    (err) => {
      if (err.name !== 'AbortError') console.error('TTS error', err);
    }
  );
  return { promise, interrupt: () => controller.abort() };
}

module.exports = { synthesizeStreaming, startInterruptibleSynthesis };
