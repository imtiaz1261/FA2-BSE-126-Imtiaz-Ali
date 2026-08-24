# Service Catalog & Purpose Classification — Module 4

Turns "what the caller said" into a bookable `service_id`, with required
documents attached.

## 1. Service catalog schema

```
{
  service_id: string,             // stable slug, e.g. "id_card_renewal"
  name: string,
  description: string,
  required_documents: string[],
  avg_duration_minutes: number,   // consumed by the Slot Engine (Module 5)
  eligible_locations: string[],   // counter/branch IDs
  example_phrases: string[],      // anchors for the classifier prompt
  active: boolean,
}
```

Defined in `src/catalog/schema.js` (with `validateServiceEntry`), persisted
via `db/migrations/001_create_services.sql`, seeded on first boot from
`SEED_SERVICES` with five entries: ID Card Renewal, New ID Card, Passport -
New, Passport - Renewal, Child Registration.

`src/catalog/catalogStore.js` provides `listServices`, `getServiceById`, and
`upsertService` — the latter is what the Admin Console (Module 11) would
call to add/edit services without a code deploy.

## 2. Classification function & confidence-threshold logic

`POST /classify` → `classifyPurpose({ utterance, language })` in
`src/classification/classifyPurpose.js`:

1. Sends the full active catalog + the caller's utterance to the LLM via a
   forced `classify_purpose` tool call, which scores **every** service
   0.0–1.0 (not just picking one) — this is what makes ambiguity detection
   possible downstream.
2. Applies two independent checks:
   - **Below threshold** (`top.confidence < CONFIDENCE_THRESHOLD`, default
     `0.75`): the model itself isn't confident this matches any known
     service well → clarify.
   - **Ambiguity margin** (`top.confidence - second.confidence < AMBIGUITY_MARGIN`,
     default `0.15`): even if the top score clears the bar, if the runner-up
     is close behind, don't guess → clarify. This is the case that catches
     "ID card" alone, which can legitimately score high for both
     `id_card_renewal` and `new_id_card`.
3. If neither check trips, returns `{ status: 'classified', service_id,
   confidence, requiredDocuments, avgDurationMinutes, eligibleLocations }`.
4. Otherwise returns `{ status: 'needs_clarification', candidates,
   clarifyingQuestion }` — a ready-to-speak question, not just raw scores.

Both thresholds are environment-configurable (`CONFIDENCE_THRESHOLD`,
`AMBIGUITY_MARGIN`) so they can be tuned from real call data without a
code change.

## 3. Clarifying questions

`src/classification/clarifyingPrompts.js` uses **template-based** questions
for known ambiguous pairs (not a fresh LLM call per ambiguity — predictable
wording, zero added latency):

| Ambiguous pair | English | Urdu |
|---|---|---|
| `id_card_renewal` vs `new_id_card` | "Just to confirm — is this to renew an ID card you already have, or to get a brand new one for the first time?" | "Sirf tasdeeq ke liye — kya yeh apni maujooda ID card ki renewal ke liye hai, ya bilkul nayi ID card banwane ke liye?" |
| `passport_new` vs `passport_renewal` | "Is this for a completely new passport, or to renew a passport you already hold?" | "Kya yeh bilkul naye passport ke liye hai, ya aapke maujooda passport ki renewal ke liye?" |

Any other ambiguous pairing falls back to a generic templated question
listing the candidate service names in the caller's language.

## 4. Integration with the Voice Agent (Module 3)

The dialogue manager's `CAPTURING_PURPOSE` state can call `POST /classify`
with the caller's utterance instead of (or as a check on) its own
`purpose_of_visit` extraction:
- `status: 'classified'` → dialogue manager sets `slots.purpose_of_visit =
  service_id`, moves to `CONFIRMING_PURPOSE`, and can read out
  `requiredDocuments` once the call reaches `FINAL_CONFIRMATION`.
- `status: 'needs_clarification'` → dialogue manager speaks
  `clarifyingQuestion` verbatim and stays in `CAPTURING_PURPOSE`.

## 5. API

```
GET  /services              -> { services: [...] }        (active only by default; ?all=true for all)
GET  /services/:serviceId   -> single service entry or 404
POST /classify               { utterance, language } -> classification result
```

## 6. Environment variables

`DATABASE_URL`, `ANTHROPIC_API_KEY`, plus optional
`CONFIDENCE_THRESHOLD`, `AMBIGUITY_MARGIN`, `CLASSIFICATION_MODEL`.

## 7. Local development

```bash
npm install
cp .env.example .env
psql "$DATABASE_URL" -f db/migrations/001_create_services.sql
npm run dev   # auto-seeds the catalog on first boot if empty
```

## Next module

Module 5 (Slot Availability Engine) consumes `avg_duration_minutes` and
`eligible_locations` from this catalog to compute real bookable slots per
service.
