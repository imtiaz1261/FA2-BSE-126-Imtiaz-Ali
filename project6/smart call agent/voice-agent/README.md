# Voice Agent — Module 3

The conversational core: STT → LLM dialogue manager → TTS, streamed in real
time over the WebSocket that `telephony-gateway`'s media-stream bridge opens
per call (`VOICE_AGENT_WS_URL` from Module 2).

## 1. Protocol (matches `telephony-gateway/src/mediaStream/bridge.js`)

Gateway → Voice Agent, per Twilio media frame:
```json
{ "type": "audio_in", "audioBase64": "<mulaw 8kHz chunk>" }
```

Voice Agent → Gateway:
```json
{ "type": "audio_out", "audioBase64": "<mulaw 8kHz chunk>" }
{ "type": "turn_result", "transcript": "...", "purpose": "passport_renewal", "parsedOk": true }
{ "type": "human_requested", "callSid": "CAxxxx" }
{ "type": "booking_ready", "callSid": "CAxxxx", "slots": { "purpose_of_visit": "...", "preferred_day": "...", "preferred_time": "..." } }
```

`turn_result.parsedOk` is what the gateway's `shouldEscalateToHuman()`
watches for its retry-count escalation path. `booking_ready` is the handoff
point to the Booking Service (Module 6) — not implemented in this module.

## 2. Dialogue-manager design

**State machine owns flow control, the LLM owns language.** `dialogue/stateMachine.js`
defines the states (mirroring Module 1's call-session state machine) and the
*only* code path that decides what state comes next. The LLM never picks
the next question — it only:
1. Extracts structured fields from the caller's utterance (`record_turn` tool call)
2. Produces the natural-language `spoken_reply` for the *current* state

This split is what keeps the flow reliable: a slightly odd LLM phrasing
never derails which slot gets asked next.

**Slot-filling order:** `purpose_of_visit` → confirm → (real availability
lookup via `check_availability` tool) → `preferred_day` → `preferred_time`
→ confirm both → final confirmation → `COMPLETED`. Each slot is echoed back
and confirmed before moving on, per the design brief.

**Prompts** (`dialogue/prompts.js`) are built per-turn from a base template
plus a state-specific instruction in the caller's detected language (English
or Urdu instructions provided; extend `STATE_INSTRUCTIONS` for more
languages). The LLM is explicitly told never to invent slot times or
tracking numbers — those only ever come from tool results.

## 3. Clarification & repeat handling

- `needs_clarification: true` in the tool output re-asks *without* advancing
  state (see `nextState()` staying in the same state when extraction fails).
- `dialogueState.clarificationAttempts` increments on each unclear turn and
  resets on success — the gateway's own retry counter (Module 2) is the one
  that actually triggers human escalation after 2 consecutive failures, so
  this counter here is primarily for logging/analytics.
- `requested_repeat: true` makes `spoken_reply` restate the previous
  question verbatim in meaning, not a generic "please repeat."

## 4. Barge-in

`stt/streamingStt.js` emits `speech_start` from the STT provider's VAD the
instant the caller starts talking. `session/callSession.js` listens for this
and calls `activeTts.interrupt()`, which aborts the in-flight TTS stream via
`AbortController` — playback stops within one network round trip, not at
the end of the current sentence. The new utterance is then processed
normally once STT emits `final`.

## 5. Language detection

Two-stage, in `language/languageDetector.js`:
1. **Script check** — Urdu Unicode range is unambiguous, instant.
2. **Roman-Urdu keyword heuristic** — catches phonetic Urdu transcribed in
   Latin script by the STT engine.
3. The LLM's `detected_language` field (part of every `record_turn` call)
   has final say once it has full sentence context, and can correct an
   initial guess mid-call if needed.

The STT session's recognition language is switched live (`stt.setLanguage()`)
the moment the initial guess resolves, and the TTS voice is selected per
`config.TTS_VOICES[language]`.

## 6. Latency budget (target: sub-1.5s per turn)

| Stage | Budget |
|---|---|
| STT finalization after caller stops speaking (`endpointing`) | ~500ms |
| LLM turn (tool-calling, bounded 6-message context window) | ~600–700ms |
| First TTS audio chunk | ~200–300ms |

Design choices that protect this budget:
- Bounded context window (`turnHistory.slice(-6)`) instead of sending full
  call history to the LLM every turn.
- At most one `check_availability` tool round-trip per turn before the
  final `record_turn` call is forced (`tool_choice: { type: 'tool', name: 'record_turn' }`).
- TTS is streamed chunk-by-chunk to the gateway rather than synthesized
  in full before sending.

## 7. Environment variables

See `src/config/env.js`. Required: `STT_API_KEY`, `TTS_API_KEY`,
`ANTHROPIC_API_KEY`, `SLOT_ENGINE_BASE_URL`, `BOOKING_SERVICE_BASE_URL`.

## 8. Local development

```bash
npm install
cp .env.example .env
npm run dev
```

Point `telephony-gateway`'s `VOICE_AGENT_WS_URL` at
`ws://localhost:4000/session` for end-to-end local testing.

## Provider notes

STT and TTS are implemented against generic streaming APIs shaped like
Deepgram (STT) and a generic streaming TTS REST endpoint shaped like Azure
Speech's streaming synthesis, both chosen because they can emit/accept
mulaw 8kHz directly — matching Twilio's Media Streams format with zero
transcoding. Swap `stt/streamingStt.js` / `tts/streamingTts.js` internals to
target a different vendor without changing any calling code, since both are
consumed only through their small public interface (`pushAudio`/events for
STT, `startInterruptibleSynthesis` for TTS).

## Next module

Module 4 (Service Catalog & Purpose Classification) formalizes the
`purpose_of_visit` taxonomy referenced in `dialogue/prompts.js`, and Module
5 (Slot Availability Engine) implements the `/availability` and `/hold`
endpoints this module's `functions/slotEngineClient.js` calls.
