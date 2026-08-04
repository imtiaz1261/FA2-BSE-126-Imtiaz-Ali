# Prompting Technique Comparison: Writing a Delay-Apology Email

**Task:** Write an email to a client informing them their order is
delayed by one week, apologizing and offering a 10% discount on their
next purchase.

**Note on these outputs:** the 5 files in `outputs/claude_demo/` were
generated directly by Claude (in this conversation) as an immediate,
concrete demonstration. Run `python run_comparison.py` with your own
Groq key to regenerate the same comparison against a Groq-hosted model
(`outputs/groq/`) -- the technique differences described below should
hold in shape even if the exact wording differs by model.

---

## What changed across techniques

| Technique | Tone | Structure | Personality | Length |
|---|---|---|---|---|
| 1. Zero-shot | Generic, formal, safe | Standard 3-paragraph email | Almost none -- reads like a template | Medium |
| 2. Few-shot | Casual-professional, matches example style | Short, punchy, matches example format closely | Picked up "Thanks for your patience", first-name greeting from examples | Short |
| 3. Role-based | Warm, direct, personally accountable | Looser, more conversational | Strongest -- signs a name, offers a personal reply channel | Longest |
| 4. Step-by-step | Neutral, thorough | Most complete -- every required element present, in order | Mechanical -- reads like a checklist was followed (because it was) | Medium-long |
| 5. Format-specific | Efficient, professional | Tightest -- literally hit every formatting constraint (word count included) | Minimal, but not robotic | Shortest, most compact |

## Key observations

- **Zero-shot** was the weakest: correct, but generic -- exactly what
  you'd expect from an under-specified prompt. It's a fine baseline,
  not a good final answer.
- **Few-shot** picked up *stylistic* cues (greeting style, sign-off,
  casualness) from the examples that zero-shot had no way to know to
  use. This is few-shot's real strength: transferring *voice*, not
  just content.
- **Role-based** produced the most human, trustworthy-sounding email
  by a clear margin -- it took ownership ("that's on us"), didn't
  over-apologize, and added a small trust-building touch (a named
  sign-off, an invitation to reply). Best choice when the *relationship*
  with the reader matters more than rigid completeness.
- **Step-by-step** guaranteed nothing was missed -- every required
  element (delay, apology, new timeframe, discount, reassurance) is
  unambiguously present. The cost is that it reads a little like a
  form filled in, because the structure is fully dictated rather than
  emergent.
- **Format-specific** was the most *reliably reusable* -- length,
  structure, and bullet formatting are exactly constrained, which
  matters if this output needs to slot into a template (e.g. a CRM
  system) without manual editing afterward.

## Which technique "wins"?

**It depends on what you're optimizing for** -- there's no single best
technique in general, only best-for-a-goal:

- Want the email to sound like *you*/your brand? → **Role-based**
- Want guaranteed inclusion of every required fact, no omissions? → **Step-by-step**
- Want output that fits a strict template/character limit automatically? → **Format-specific**
- Want to match an existing style you already have examples of? → **Few-shot**
- Want a quick, safe draft with minimal setup? → **Zero-shot** (but expect to edit it)

For *this specific task* (a client-facing apology email), **role-based**
produced the best single output on its own -- it's the one most likely
to be sent with zero edits, because tone matters more than technical
completeness in an apology email. But in practice, the strongest
real-world prompt often **combines techniques**: role-based tone +
format-specific constraints + a couple of few-shot examples of your
brand's actual past emails.

## Suggested next step

Run `python run_comparison.py` with your Groq key, then edit the table
above with the Groq-generated outputs to see whether the same pattern
holds on a different model -- that's a genuinely useful thing to note
in a submission: do these technique effects generalize across models,
or are they model-specific?
