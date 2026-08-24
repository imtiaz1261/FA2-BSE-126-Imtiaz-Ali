const { StreamingSttSession } = require('../stt/streamingStt');
const { startInterruptibleSynthesis } = require('../tts/streamingTts');
const { runDialogueTurn } = require('../dialogue/llmDialogueManager');
const { initialDialogueState, nextState, STATES, allSlotsFilled } = require('../dialogue/stateMachine');
const { resolveInitialLanguage } = require('../language/languageDetector');
const { checkAvailability } = require('../functions/slotEngineClient');

/**
 * One instance per phone call. Bridges:
 *   Twilio audio (via telephony-gateway's WS) -> STT -> dialogue manager -> TTS -> Twilio audio
 *
 * Emits messages back over `send` matching the protocol the telephony
 * gateway's mediaStream/bridge.js expects:
 *   { type: 'audio_out', audioBase64 }
 *   { type: 'turn_result', transcript, purpose, parsedOk }
 */
class CallSession {
  constructor({ callSid, send }) {
    this.callSid = callSid;
    this.send = send; // function(messageObject) -> forwards to the gateway WS
    this.dialogueState = initialDialogueState();
    this.activeTts = null; // { promise, interrupt } while TTS is playing
    this.firstUtteranceSeen = false;

    this.stt = new StreamingSttSession({ language: this.dialogueState.language });
    this._wireSttEvents();

    this._speak(this._greetingText());
  }

  _wireSttEvents() {
    this.stt.on('speech_start', () => {
      // Barge-in: if we're mid-TTS when the caller starts talking, cut
      // playback immediately rather than waiting for them to finish.
      if (this.activeTts) {
        this.activeTts.interrupt();
        this.activeTts = null;
      }
    });

    this.stt.on('final', async ({ transcript }) => {
      await this._handleFinalTranscript(transcript);
    });

    this.stt.on('error', (err) => {
      console.error(`STT error on call ${this.callSid}`, err);
      this.send({ type: 'turn_result', transcript: '', purpose: null, parsedOk: false });
    });
  }

  async _handleFinalTranscript(transcript) {
    if (!transcript || !transcript.trim()) return;

    if (!this.firstUtteranceSeen) {
      this.firstUtteranceSeen = true;
      const detected = resolveInitialLanguage(transcript);
      this.dialogueState.language = detected;
      this.stt.setLanguage(detected);
    }

    let turnOutput;
    try {
      turnOutput = await runDialogueTurn({
        dialogueState: this.dialogueState,
        callerUtterance: transcript,
      });
    } catch (err) {
      console.error(`Dialogue manager error on call ${this.callSid}`, err);
      this.send({ type: 'turn_result', transcript, purpose: null, parsedOk: false });
      return;
    }

    // Persist any language correction the LLM made with fuller context.
    if (turnOutput.detected_language) {
      this.dialogueState.language = turnOutput.detected_language;
    }

    // Merge newly extracted slot values (never overwrite a filled slot with null).
    for (const [key, value] of Object.entries(turnOutput.extracted || {})) {
      if (value) this.dialogueState.slots[key] = value;
    }

    this.dialogueState.turnHistory.push(
      { role: 'user', content: transcript },
      { role: 'assistant', content: turnOutput.spoken_reply }
    );

    // Report this turn upward so the telephony gateway's fallback logic
    // (Module 2) can decide whether to escalate to a human.
    this.send({
      type: 'turn_result',
      transcript,
      purpose: this.dialogueState.slots.purpose_of_visit,
      parsedOk: turnOutput.parsedOk && !turnOutput.needs_clarification,
    });

    if (turnOutput.requested_human) {
      // telephony-gateway handles the actual transfer once it sees a
      // turn_result with parsedOk=false repeatedly, or can be extended to
      // read an explicit `requested_human` flag directly — surfaced here
      // for that extension point.
      this.send({ type: 'human_requested', callSid: this.callSid });
    }

    this.dialogueState.clarificationAttempts = turnOutput.needs_clarification
      ? this.dialogueState.clarificationAttempts + 1
      : 0;

    await this._advanceState(turnOutput);
    await this._speak(turnOutput.spoken_reply);
  }

  async _advanceState(turnOutput) {
    const prevState = this.dialogueState.state;
    this.dialogueState.state = nextState(this.dialogueState, turnOutput);

    // Entering CHECKING_SLOTS: fetch real availability before asking for
    // day/time, so the agent can offer options grounded in reality instead
    // of guessing, then immediately move on to CAPTURING_DAY.
    if (prevState !== STATES.CHECKING_SLOTS && this.dialogueState.state === STATES.CHECKING_SLOTS) {
      try {
        const availability = await checkAvailability({
          serviceType: this.dialogueState.slots.purpose_of_visit,
        });
        this.dialogueState.availableSlotsCache = availability;
      } catch (err) {
        console.error('Slot Engine lookup failed', err);
        this.dialogueState.availableSlotsCache = { hasAvailability: false, slots: [] };
      }
    }

    if (this.dialogueState.state === STATES.COMPLETED) {
      this.send({
        type: 'booking_ready',
        callSid: this.callSid,
        slots: this.dialogueState.slots,
      });
    }
  }

  _greetingText() {
    return this.dialogueState.language === 'ur'
      ? 'Assalam-o-Alaikum, citizen services mein khush aamdeed. Aap aaj kis silsile mein call kar rahe hain?'
      : 'Hello, thank you for calling citizen services. What can I help you with today?';
  }

  async _speak(text) {
    this.activeTts = startInterruptibleSynthesis({
      text,
      language: this.dialogueState.language,
      onChunk: (audioBase64) => this.send({ type: 'audio_out', audioBase64 }),
    });
    await this.activeTts.promise;
    this.activeTts = null;
  }

  /** Called by the WS server for every inbound Twilio media frame. */
  pushAudio(audioBase64) {
    this.stt.pushAudio(audioBase64);
  }

  close() {
    this.stt.close();
    if (this.activeTts) this.activeTts.interrupt();
  }
}

module.exports = { CallSession, allSlotsFilled };
