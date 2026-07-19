# Case Study: Would SDIE Have Caught Blockbuster's Netflix Mistake?

**A hindcast validation of the Strategic Decision Intelligence Engine (SDIE), using the platform's own live API.**

---

## The setup

In 2000, Netflix co-founders Reed Hastings and Marc Randolph flew to Dallas and offered to
sell Netflix to Blockbuster for **$50 million**. Netflix was unprofitable, with fewer than
300,000 subscribers. Blockbuster operated over 9,000 stores, served roughly 60 million
customers, and reported approximately **$6 billion in annual revenue** in its FY2000 10-Q
filed with the SEC. Netflix's own pitch was explicit: Netflix would run Blockbuster's online
business, and Blockbuster would promote Netflix in its stores — a combined physical-and-digital
offering. Blockbuster's leadership declined. Ten years later, Netflix had over 20 million
subscribers and $2.16 billion in revenue; Blockbuster filed for bankruptcy the same year.

This is one of the most cited strategic misjudgments in modern corporate history. The
question this case study asks is narrow and testable: **using only the information a
Blockbuster executive had access to in 2000, would a structured decision framework have
surfaced the right call?**

All figures below are cited to public sources (SEC EDGAR, contemporaneous and retrospective
reporting on the meeting itself — see citations). The MCDA criterion *scores* are this
analyst's judgment calls, made using only information that was genuinely available at the
time — they are not themselves sourced data, and that distinction is kept explicit throughout.

## Running it through SDIE

**Method:** Multi-criteria decision analysis (weighted-sum model), SDIE's `decision_analysis`
context — the same engine used for any build-vs-buy decision on the platform.

**Options:**
- Acquire Netflix for $50M
- Decline the offer

**Criteria and weights** (reflecting what a board evaluating this in 2000 would actually be
weighing):

| Criterion | Weight | Why this weight |
|---|---|---|
| Acquisition cost | 0.15 | $50M was well under 1% of Blockbuster's ~$6B annual revenue — material, but not a bet-the-company sum |
| Strategic fit with digital distribution | 0.35 | Netflix's own pitch was explicit about building a combined physical/digital offering |
| Near-term cannibalization risk | 0.15 | A real, legitimate board concern — Blockbuster's late-fee revenue model was a going concern |
| Downside protection against disruption | 0.35 | The core "optionality" question: does declining hand a potential disruptor the field, uncontested? |

## What SDIE returned

```
POST /api/v1/decision-analysis/mcda/rank
```

| Option | Weighted score |
|---|---|
| **Acquire Netflix for $50M** | **0.70** |
| Decline the offer | 0.30 |

**Recommended option: Acquire Netflix for $50M** — a 0.4 margin, not a coin flip.

The more interesting output is the **robustness check** SDIE runs automatically on every MCDA
result: how far would a criterion's weight have to move before the recommendation flips?

| Criterion | Current weight | Flips at | Direction needed to flip |
|---|---|---|---|
| Acquisition cost | 0.15 | **0.40** | increase |
| Near-term cannibalization risk | 0.15 | **0.40** | increase |
| Strategic fit | 0.35 | — | never flips |
| Downside protection | 0.35 | — | never flips |

In plain terms: a skeptical board member would have had to treat the **$50M price tag as
more important than everything else on the table combined** — nearly triple its actual
weight — before "decline" becomes the right call. This is the number that would have been
useful in the room in 2000: not just "acquire looks better," but "acquire looks better under
almost any reasonable disagreement about how much the price tag should matter."

## The generated deliverable

SDIE's `recommendation_synthesis` context fused this MCDA result with the cited evidence
into a `DecisionRationale`, then rendered it as an actual one-page PDF memo via the
platform's board-ready export — not a mockup, the real output of `GET
/recommendation-synthesis/rationales/{id}/one-pager`:

**→ [blockbuster-netflix-memo.pdf](blockbuster-netflix-memo.pdf)**

## What actually happened (the hindcast)

Blockbuster declined. By 2010: Netflix had scaled past 20M subscribers with $2.16B in
revenue; Blockbuster filed for bankruptcy the same year. Netflix's later valuation exceeded
$150B. The retrospective consensus (including from Blockbuster's own former executives) is
that this was a strategic failure to recognize disruption, not a defensible bet that didn't
pay off.

## What this case study does and doesn't claim

**Does claim:** a structured, weighted, robustness-checked framework — using only
information available at the time — points clearly and *robustly* toward the acquisition,
and does so in a way that's auditable rather than a single analyst's gut call.

**Does not claim:** that MCDA "predicted" a $150B outcome, that the specific weights chosen
here are the only defensible ones, or that structured frameworks guarantee good decisions.
The value demonstrated here is narrower and more honest: this is what the *process* of
checking an intuitive call against a structured, robustness-tested framework looks like —
and in this case, it would have flagged that declining was the fragile choice, not the safe
one.

## Reproducing this

Every number above came from the live API, not a script written to produce this result:

```bash
POST /api/v1/decision-analysis/mcda/rank        # → analysis_id, rankings, weight_robustness
POST /api/v1/recommendation-synthesis/rationales # → rationale_id, fused with cited evidence
GET  /api/v1/recommendation-synthesis/rationales/{id}/one-pager  # → the PDF above
```

---

*Sources: Blockbuster Inc. Form 10-Q, FY2000 (SEC EDGAR); Newsweek, "Fact Check: Did
Blockbuster Turn Down Chance to Buy Netflix for $50 Million" (2021); ScreenGeek, "Blockbuster
Turned Down Chance To Buy Netflix In 2000" (2024).*
