const WebSocket = require('ws');
const { EventEmitter } = require('events');
const config = require('../config/env');

/**
 * Provider-agnostic streaming STT session. Emits:
 *   'speech_start'   - caller started talking (used for barge-in)
 *   'partial'        - interim transcript, low latency, may change
 *   'final'          - finalized transcript for one utterance
 *   'error'
 *
 * Reference implementation targets Deepgram's streaming API (WS, mulaw
 * 8kHz to match Twilio Media Streams audio format directly — no
 * resampling needed). Swap the connection URL/format mapping to switch
 * providers (Google STT, Azure Speech, etc.) without touching callers of
 * this class.
 */
class StreamingSttSession extends EventEmitter {
  constructor({ language = 'en' } = {}) {
    super();
    this.language = language;
    this.ws = null;
    this._connect();
  }

  _connect() {
    const langParam = this.language === 'ur' ? 'ur' : 'en';
    const url =
      `wss://api.deepgram.com/v1/listen` +
      `?encoding=mulaw&sample_rate=8000&channels=1` +
      `&language=${langParam}&interim_results=true&endpointing=${config.STT_FINAL_SILENCE_MS}` +
      `&vad_events=true`;

    this.ws = new WebSocket(url, {
      headers: { Authorization: `Token ${config.STT_API_KEY}` },
    });

    this.ws.on('message', (raw) => this._handleMessage(raw));
    this.ws.on('error', (err) => this.emit('error', err));
    this.ws.on('close', () => this.emit('closed'));
  }

  _handleMessage(raw) {
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }

    if (msg.type === 'SpeechStarted') {
      this.emit('speech_start');
      return;
    }

    if (msg.type === 'Results') {
      const alt = msg.channel?.alternatives?.[0];
      if (!alt || !alt.transcript) return;

      if (msg.is_final) {
        this.emit('final', { transcript: alt.transcript, confidence: alt.confidence });
      } else {
        this.emit('partial', { transcript: alt.transcript });
      }
    }
  }

  /** Feed raw base64 mulaw audio straight from Twilio's media frames. */
  pushAudio(audioBase64) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(Buffer.from(audioBase64, 'base64'));
    }
  }

  /** Switch recognition language mid-call once detection resolves/updates. */
  setLanguage(language) {
    if (language === this.language) return;
    this.language = language;
    this.ws.close();
    this._connect();
  }

  close() {
    if (this.ws.readyState === WebSocket.OPEN) this.ws.close();
  }
}

module.exports = { StreamingSttSession };
