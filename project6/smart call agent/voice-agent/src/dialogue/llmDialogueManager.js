const Anthropic = require('@anthropic-ai/sdk');
const config = require('../config/env');
const { RECORD_TURN_TOOL, buildSystemPrompt } = require('./prompts');
const { CHECK_AVAILABILITY_TOOL, checkAvailability } = require('../functions/slotEngineClient');

const anthropic = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });

/**
 * Runs one dialogue turn:
 *  - Sends the recent turn history + current state instruction to the LLM.
 *  - The LLM may call `check_availability` (real data, executed here and
 *    fed back) before producing its final `record_turn` tool call.
 *  - Returns the structured extraction + the natural-language reply to
 *    synthesize via TTS.
 *
 * Kept as a single request/response function (rather than a long-lived
 * chat session on the LLM side) so each turn's latency is predictable and
 * we control exactly what context window is sent — important for staying
 * inside the sub-1.5s per-turn budget.
 */
async function runDialogueTurn({ dialogueState, callerUtterance }) {
  const { state, slots, language, turnHistory } = dialogueState;

  const systemPrompt = buildSystemPrompt({ state, slots, language });

  const messages = [
    ...turnHistory.slice(-6), // bounded context: last 3 exchanges is plenty for slot-filling
    { role: 'user', content: callerUtterance },
  ];

  let response = await anthropic.messages.create({
    model: config.DIALOGUE_MODEL,
    max_tokens: 400,
    system: systemPrompt,
    messages,
    tools: [RECORD_TURN_TOOL, CHECK_AVAILABILITY_TOOL],
    tool_choice: { type: 'auto' },
  });

  // Tool-use loop: handle at most one availability lookup per turn before
  // requiring the final record_turn call, to bound latency.
  let toolUse = response.content.find((b) => b.type === 'tool_use');
  if (toolUse && toolUse.name === 'check_availability') {
    const availability = await checkAvailability(toolUse.input).catch((err) => ({
      error: err.message,
    }));

    messages.push({ role: 'assistant', content: response.content });
    messages.push({
      role: 'user',
      content: [
        {
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: JSON.stringify(availability),
        },
      ],
    });

    response = await anthropic.messages.create({
      model: config.DIALOGUE_MODEL,
      max_tokens: 400,
      system: systemPrompt,
      messages,
      tools: [RECORD_TURN_TOOL, CHECK_AVAILABILITY_TOOL],
      tool_choice: { type: 'tool', name: 'record_turn' }, // force the final structured output
    });
    toolUse = response.content.find((b) => b.type === 'tool_use');
  }

  if (!toolUse || toolUse.name !== 'record_turn') {
    // Defensive fallback: should not normally happen with tool_choice set,
    // but never let a malformed model response crash the call.
    return {
      extracted: { purpose_of_visit: null, preferred_day: null, preferred_time: null },
      confirmation: 'not_applicable',
      needs_clarification: true,
      requested_repeat: false,
      requested_human: false,
      detected_language: language,
      spoken_reply:
        language === 'ur'
          ? 'Maazrat, mujhe samajh nahi aaya. Kya aap dobara bata sakte hain?'
          : "Sorry, I didn't quite catch that. Could you say that again?",
      parsedOk: false,
    };
  }

  return { ...toolUse.input, parsedOk: true };
}

module.exports = { runDialogueTurn };
