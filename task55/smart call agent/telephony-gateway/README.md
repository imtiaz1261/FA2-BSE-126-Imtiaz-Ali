# Telephony Gateway — Module 2

Call-routing layer for the Smart Appointment Call Agent. Answers inbound calls,
plays the consent notice, bridges real-time audio to the Voice Agent (Module 3),
and handles all fallback/escalation paths to a human queue.

## 1. Provisioning a phone number (Twilio Voice example)

1. Buy/port a number in the Twilio Console (or via `POST /IncomingPhoneNumbers`),
   ideally a local number for the citizen-service region.
2. Set its **Voice Configuration**:
   - "A call comes in" → **Webhook**, HTTP POST → `https://<your-domain>/voice`
   - Fallback URL → same domain, `https://<your-domain>/voice/fallback/transfer?reason=agent_error`
     (Twilio calls this automatically if the primary webhook times out or 5xxs)
3. Set `TWILIO_SERVICE_NUMBER` and other values in `.env` (see `src/config/env.js`).

## 2. Request flow

```
Citizen dials number
  -> POST /voice                      (webhooks/incomingCall.js)
       - checks queue depth (skip AI entirely if overloaded)
       - plays consent/recording notice
       - starts recording
       - <Connect><Stream> opens WS to /media-stream
  -> WS /media-stream                 (mediaStream/bridge.js)
       - relays caller audio to Voice Agent backend
       - relays synthesized speech back to caller
       - on each turn, checks shouldEscalateToHuman()
  -> POST /voice/fallback/transfer    (webhooks/fallback.js)   [if escalated]
       - enqueues call into human ACD queue with context
  -> POST /voice/fallback/agent-whisper                        [agent picks up]
       - reads captured purpose + escalation reason to staff before connecting
```

## 3. Fallback triggers (implemented in `fallback/humanHandoff.js`)

| Trigger | Behavior |
|---|---|
| Caller says a trigger phrase ("talk to a person", etc.) | Immediate transfer, context passed along |
| Voice agent fails to parse intent 2 turns in a row | Auto-escalate (`MAX_NO_RESPONSE_RETRIES`) |
| Voice-agent backend errors/times out | Auto-escalate (`agent_error`) |
| System under high load at call start | Route directly to queue, skip AI agent, play wait estimate |

## 4. Call queueing

`queue/callQueue.js` exposes:
- `getQueueDepth()` — live queue size from the Twilio Queue resource
- `estimateWaitSeconds()` — depth / active agents × average handle time
- `POST /voice/queue/hold-music` — Twilio's `waitUrl`, re-announces the
  updated estimate and plays hold music while the caller is queued

Tune `AVG_HANDLE_TIME_SECONDS` and `ASSUMED_ACTIVE_AGENTS` from real
call-center data once available; swap in a proper Erlang-C calculator
for production-grade estimates.

## 5. Recording & consent

- The consent notice (`CONSENT_NOTICE_TEXT` in `config/env.js`) is played
  **before** `<Record>` starts, satisfying "notice before recording" rules.
- `recording/recordingControl.js` provides a REST-API alternative for
  starting/pausing/resuming/stopping recording programmatically, useful if
  you need to pause recording around any future sensitive data capture.
- Wire an opt-out: if STT detects "do not record" during the notice window,
  call `stopRecording()` immediately and log the opt-out on the session.

## 6. Environment variables

See `src/config/env.js` for the full list. Required:
`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SERVICE_NUMBER`,
`MEDIA_STREAM_WSS_URL`, `VOICE_AGENT_WS_URL`, `PUBLIC_BASE_URL`.

## 7. Local development

```bash
npm install
cp .env.example .env   # fill in Twilio + Redis + voice-agent URLs
npm run dev
# expose localhost via ngrok/Twilio CLI tunnel for the webhook URLs
```

## Next module

Module 3 (Conversational Voice Agent) implements the `VOICE_AGENT_WS_URL`
backend this gateway connects to: STT → NLU/Dialogue Manager → TTS, and is
what produces the `turn_result` / `audio_out` messages this bridge relays.
