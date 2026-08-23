const Anthropic = require('@anthropic-ai/sdk');
const config = require('../config/env');
const { listServices } = require('../catalog/catalogStore');
const { buildClarifyingQuestion } = require('./clarifyingPrompts');

const anthropic = new Anthropic({ apiKey: config.ANTHROPIC_API_KEY });

const CLASSIFY_TOOL = {
  name: 'classify_purpose',
  description: 'Scores how well the caller\'s stated purpose matches each candidate service.',
  input_schema: {
    type: 'object',
    properties: {
      scores: {
        type: 'array',
        description: 'One entry per candidate service_id provided, each with a confidence score.',
        items: {
          type: 'object',
          properties: {
            service_id: { type: 'string' },
            confidence: {
              type: 'number',
              description: '0.0 to 1.0 — how confident this utterance matches this service.',
            },
          },
          required: ['service_id', 'confidence'],
        },
      },
    },
    required: ['scores'],
  },
};

function buildSystemPrompt(services) {
  const catalogDescription = services
    .map(
      (s) =>
        `- ${s.service_id}: ${s.name} — ${s.description} (examples: ${s.example_phrases
          .slice(0, 3)
          .join('; ')})`
    )
    .join('\n');

  return `You are classifying a citizen's spoken reason for calling a government service center into one of the following services. Score EVERY service listed, even if the score is 0 — do not omit any.

${catalogDescription}

Score based on semantic match to the caller's utterance, not exact keyword overlap. The utterance may be in English, Urdu, or Roman Urdu. If the utterance is genuinely ambiguous between two services (e.g. mentions "ID card" without saying new or renewal), give both plausible services similarly high scores rather than arbitrarily picking one.`;
}

/**
 * Classifies a caller's free-form utterance against the active service
 * catalog.
 *
 * Returns one of:
 *  - { status: 'classified', service_id, confidence, requiredDocuments }
 *  - { status: 'needs_clarification', candidates, clarifyingQuestion }
 *
 * Confidence-threshold logic:
 *  1. If the top score is below CONFIDENCE_THRESHOLD, ask for clarification
 *     (the model itself isn't sure this is any of our known services well).
 *  2. If the top score clears the threshold but the second-best score is
 *     within AMBIGUITY_MARGIN of it, treat it as ambiguous anyway — this
 *     catches cases like "ID card" alone, which can legitimately score
 *     high for both id_card_renewal and new_id_card.
 */
async function classifyPurpose({ utterance, language = 'en' }) {
  const services = await listServices({ activeOnly: true });

  const response = await anthropic.messages.create({
    model: config.CLASSIFICATION_MODEL,
    max_tokens: 500,
    system: buildSystemPrompt(services),
    messages: [{ role: 'user', content: utterance }],
    tools: [CLASSIFY_TOOL],
    tool_choice: { type: 'tool', name: 'classify_purpose' },
  });

  const toolUse = response.content.find((b) => b.type === 'tool_use');
  const scores = toolUse?.input?.scores || [];

  const ranked = scores
    .map((s) => ({ ...s, service: services.find((svc) => svc.service_id === s.service_id) }))
    .filter((s) => s.service) // drop hallucinated service_ids defensively
    .sort((a, b) => b.confidence - a.confidence);

  if (ranked.length === 0) {
    return {
      status: 'needs_clarification',
      candidates: services,
      clarifyingQuestion: buildClarifyingQuestion({ candidates: services.slice(0, 2), language }),
    };
  }

  const top = ranked[0];
  const second = ranked[1];

  const belowThreshold = top.confidence < config.CONFIDENCE_THRESHOLD;
  const tooClose = second && top.confidence - second.confidence < config.AMBIGUITY_MARGIN;

  if (belowThreshold || tooClose) {
    const candidateServices = (tooClose ? [top, second] : ranked.slice(0, 2)).map((r) => r.service);
    return {
      status: 'needs_clarification',
      candidates: candidateServices,
      clarifyingQuestion: buildClarifyingQuestion({ candidates: candidateServices, language }),
    };
  }

  return {
    status: 'classified',
    service_id: top.service_id,
    confidence: top.confidence,
    requiredDocuments: top.service.required_documents,
    avgDurationMinutes: top.service.avg_duration_minutes,
    eligibleLocations: top.service.eligible_locations,
  };
}

module.exports = { classifyPurpose };
