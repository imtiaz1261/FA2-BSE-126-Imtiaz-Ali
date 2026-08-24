/**
 * Prompt design for the LLM dialogue manager.
 *
 * Design principles:
 *  - One state = one focused instruction. We never hand the LLM the whole
 *    flow and ask it to "figure out what to ask next" — the state machine
 *    (dialogue/stateMachine.js) already knows that. The LLM's job per turn
 *    is: (a) extract structured data from what the caller just said, and
 *    (b) phrase a natural, non-robotic response for the *current* state.
 *  - Structured output via tool-calling, not free-text parsing. The model
 *    always returns a `record_turn` tool call so extraction is reliable
 *    even when the spoken reply is conversational ("uh yeah next Tuesday
 *    works, maybe morning?").
 *  - Confirmation is mandatory and explicit, never inferred from tone.
 *  - Bilingual: the same tool schema is reused across languages; only the
 *    natural-language system instructions and spoken_reply differ.
 */

const RECORD_TURN_TOOL = {
  name: 'record_turn',
  description:
    'Records what was understood from the caller in this turn and the natural-language reply to speak back.',
  input_schema: {
    type: 'object',
    properties: {
      detected_language: {
        type: 'string',
        enum: ['en', 'ur'],
        description: 'Language the caller is speaking, based on this and prior turns.',
      },
      extracted: {
        type: 'object',
        properties: {
          purpose_of_visit: {
            type: ['string', 'null'],
            description:
              'Normalized service type, e.g. "id_card_renewal", "new_id_card", "passport_new", "passport_renewal". Null if not yet clear.',
          },
          preferred_day: {
            type: ['string', 'null'],
            description: 'ISO date (YYYY-MM-DD) if resolvable, else a relative phrase like "next Tuesday". Null if not given this turn.',
          },
          preferred_time: {
            type: ['string', 'null'],
            description: '24h HH:MM if resolvable, else a phrase like "morning". Null if not given this turn.',
          },
        },
        required: ['purpose_of_visit', 'preferred_day', 'preferred_time'],
      },
      confirmation: {
        type: 'string',
        enum: ['yes', 'no', 'unclear', 'not_applicable'],
        description:
          'If the previous turn asked the caller to confirm a slot, classify their reply. "not_applicable" if this turn is not a confirmation question.',
      },
      needs_clarification: {
        type: 'boolean',
        description: 'True if the caller\'s answer was off-topic, ambiguous, or unintelligible and must be re-asked.',
      },
      requested_repeat: {
        type: 'boolean',
        description: 'True if the caller asked the agent to repeat itself.',
      },
      requested_human: {
        type: 'boolean',
        description: 'True if the caller explicitly asked for a human agent.',
      },
      spoken_reply: {
        type: 'string',
        description:
          'The exact natural-language sentence(s) to speak back to the caller next, in detected_language. Conversational, not robotic. Must include an explicit confirmation readback when confirming a slot.',
      },
    },
    required: ['detected_language', 'extracted', 'confirmation', 'needs_clarification', 'requested_repeat', 'requested_human', 'spoken_reply'],
  },
};

const BASE_SYSTEM_PROMPT = `You are a warm, efficient voice assistant for a citizen services appointment line (ID card renewal, new ID card, passport services). You are speaking on a live phone call — keep every spoken_reply short (1-2 sentences), natural, and easy to say out loud. Never sound like you are reading a form.

Rules:
- Ask only about the current slot in focus (given below as CURRENT_STATE). Do not ask about future slots early, even if the caller volunteers information — if they do volunteer it, extract it into the right field anyway so we don't ask again.
- Always confirm a slot back to the caller in your own words before moving on ("Got it, ID card renewal — is that right?").
- If the caller's answer doesn't make sense for the current question, or is off-topic, set needs_clarification=true and write a polite, specific re-ask (not a generic "please repeat").
- If the caller asks you to repeat, set requested_repeat=true and spoken_reply should simply restate your previous question, unchanged in meaning.
- If the caller asks for a human / operator / representative at any point, set requested_human=true.
- Continue the conversation in detected_language for the rest of the call once a language is confidently established from the first 1-2 turns.
- Never invent appointment slots, dates, or confirmation numbers yourself — those come from tool results provided to you separately.

CURRENT_STATE: {{STATE}}
STATE_INSTRUCTION: {{STATE_INSTRUCTION}}
SLOTS_SO_FAR: {{SLOTS_JSON}}
LANGUAGE: {{LANGUAGE}}`;

const STATE_INSTRUCTIONS = {
  GREETING: {
    en: 'Greet the caller briefly and ask what they are calling about today (purpose of visit).',
    ur: 'Caller ko mukhtasar khush-amdeed kahein aur pochein woh aaj kis silsile mein call kar rahe hain.',
  },
  CAPTURING_PURPOSE: {
    en: 'Determine the purpose of visit. If unclear, ask a clarifying question with example options (ID card renewal, new ID card, passport appointment).',
    ur: 'Maloom karein caller ka maqsad kya hai. Agar wazeh na ho, misalon ke sath dobara pochein (ID card renewal, naya ID card, passport appointment).',
  },
  CONFIRMING_PURPOSE: {
    en: 'Read back the captured purpose in plain language and ask the caller to confirm yes/no.',
    ur: 'Samjha gaya maqsad asaan alfaaz mein dohrayein aur caller se haan/na mein tasdeeq maangein.',
  },
  CAPTURING_DAY: {
    en: 'Ask what day the caller would prefer to come in, mentioning the range of available days if known.',
    ur: 'Pochein caller kis din aana pasand karenge, agar maloom ho to dastiyab dinon ka zikar karein.',
  },
  CAPTURING_TIME: {
    en: 'Ask what time of day the caller prefers, given the confirmed day.',
    ur: 'Confirm shuda din ke liye pochein caller din ke kis waqt aana chahenge.',
  },
  CONFIRMING_DATETIME: {
    en: 'Read back the exact day and time and ask the caller to confirm yes/no before finalizing.',
    ur: 'Exact din aur waqt dohrayein aur finalize karne se pehle haan/na mein tasdeeq maangein.',
  },
  FINAL_CONFIRMATION: {
    en: 'Tell the caller their appointment is confirmed and a tracking number and SMS confirmation are on the way.',
    ur: 'Caller ko batayein ke unki appointment confirm ho gayi hai aur tracking number SMS ke zariye bheja ja raha hai.',
  },
};

function buildSystemPrompt({ state, slots, language }) {
  const instruction = STATE_INSTRUCTIONS[state]?.[language] || STATE_INSTRUCTIONS[state]?.en || '';
  return BASE_SYSTEM_PROMPT
    .replace('{{STATE}}', state)
    .replace('{{STATE_INSTRUCTION}}', instruction)
    .replace('{{SLOTS_JSON}}', JSON.stringify(slots))
    .replace('{{LANGUAGE}}', language);
}

module.exports = { RECORD_TURN_TOOL, buildSystemPrompt, STATE_INSTRUCTIONS };
