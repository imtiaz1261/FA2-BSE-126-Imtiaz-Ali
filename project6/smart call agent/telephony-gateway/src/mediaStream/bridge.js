const WebSocket = require('ws');
const twilio = require('twilio');
const config = require('../config/env');
const { updateSession } = require('../fallback/sessionStore');
const { shouldEscalateToHuman } = require('../fallback/humanHandoff');

const twilioClient = twilio(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN);

/**
 * Twilio's Media Streams protocol sends JSON frames over this socket:
 *   { event: "start", start: { callSid, streamSid, ... } }
 *   { event: "media", media: { payload: <base64 mulaw audio> } }
 *   { event: "stop" }
 *
 * This bridge forwards inbound audio to the voice-agent backend and relays
 * the agent's synthesized speech back to Twilio as outbound media frames.
 */
function attachMediaStreamBridge(wss) {
  wss.on('connection', (twilioWs) => {
    let callSid = null;
    let streamSid = null;
    let agentWs = null;

    twilioWs.on('message', async (raw) => {
      const msg = JSON.parse(raw);

      switch (msg.event) {
        case 'start': {
          callSid = msg.start.callSid;
          streamSid = msg.start.streamSid;

          // Open a companion connection to the voice-agent backend for
          // this call (Module 3: STT -> NLU/Dialogue -> TTS).
          agentWs = new WebSocket(`${config.VOICE_AGENT_WS_URL}?callSid=${callSid}`);

          agentWs.on('message', async (agentMsg) => {
            const parsed = JSON.parse(agentMsg);

            if (parsed.type === 'audio_out') {
              // Relay synthesized TTS audio back to the caller.
              twilioWs.send(
                JSON.stringify({
                  event: 'media',
                  streamSid,
                  media: { payload: parsed.audioBase64 },
                })
              );
              return;
            }

            if (parsed.type === 'turn_result') {
              // Track captured purpose for later human-handoff context.
              if (parsed.purpose) {
                await updateSession(callSid, { purposeSoFar: parsed.purpose });
              }

              const decision = await shouldEscalateToHuman({
                callSid,
                transcript: parsed.transcript,
                agentParsedOk: parsed.parsedOk,
                agentError: false,
              });

              if (decision.escalate) {
                await redirectCallToHuman(callSid, decision.reason);
              }
            }
          });

          agentWs.on('error', async (err) => {
            console.error('voice-agent connection error', err);
            const decision = await shouldEscalateToHuman({
              callSid,
              transcript: '',
              agentParsedOk: false,
              agentError: true,
            });
            if (decision.escalate) {
              await redirectCallToHuman(callSid, decision.reason);
            }
          });
          break;
        }

        case 'media': {
          // Forward raw caller audio to the voice-agent backend for STT.
          if (agentWs && agentWs.readyState === WebSocket.OPEN) {
            agentWs.send(
              JSON.stringify({ type: 'audio_in', audioBase64: msg.media.payload })
            );
          }
          break;
        }

        case 'stop': {
          if (agentWs) agentWs.close();
          break;
        }
      }
    });

    twilioWs.on('close', () => {
      // Caller hung up mid-call: close the agent socket and let the
      // fallback layer's slot-hold TTL (in the Slot Engine / Redis)
      // release any held appointment slot as a safety net.
      if (agentWs) agentWs.close();
    });
  });
}

/**
 * Mid-call redirect: uses the Twilio REST API to update a live call with
 * new TwiML that routes it into the human queue (see webhooks/fallback.js).
 */
async function redirectCallToHuman(callSid, reason) {
  await twilioClient.calls(callSid).update({
    url: `${config.PUBLIC_BASE_URL}/voice/fallback/transfer?reason=${encodeURIComponent(
      reason
    )}`,
    method: 'POST',
  });
}

module.exports = { attachMediaStreamBridge };
