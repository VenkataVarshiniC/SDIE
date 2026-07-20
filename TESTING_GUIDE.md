# SDIE — Testing Guide

Every example below is a real request/response pair, captured by actually running it against
a live local instance — nothing here is hand-written JSON. Use these as a walkthrough: run them
in order (each one's output feeds the next), either via the frontend forms or by copying the
`curl` commands directly.

**Setup for the curl examples:** every request needs two headers (the stub auth — see
`shared_kernel/infrastructure/auth.py`):
```
-H "X-Tenant-Id: 00000000-0000-0000-0000-0000000000dd"
-H "X-User-Id: 00000000-0000-0000-0000-000000000002"
```
Base URL: `http://localhost:8000/api/v1`. In the frontend these headers are set automatically.

---

## 1. Workspace — `/dashboard/workspace`

**Input** (the "New engagement" form):
```json
POST /workspace/engagements
{"title": "EU market entry decision"}
```

**Output:**
```json
{
  "engagement_id": "286deaa7-d96a-4d63-ad7a-5c200a9bdffe",
  "title": "EU market entry decision",
  "status": "framing",
  "problem_framing_analysis_id": null,
  "evidence_document_ids": [],
  "financial_model_id": null,
  "decision_analysis_id": null,
  "rationale_id": null,
  "created_at": "2026-07-20T05:12:59.862414Z"
}
```

The detail page (`/dashboard/workspace/{id}`) shows five stages, each starting unlinked. As you
complete Sections 2–6 below **from this engagement's stepper page** (not the standalone tool
pages), each artifact auto-links back here and `status` advances. See Section 8 for the full
lifecycle recap.

---

## 2. Problem Framing — `/dashboard/problem-framing`

**Input 1** — load a template:
```
GET /problem-framing/templates/five_forces
```
**Output** (all 5 sections, one shown):
```json
[
  {
    "key": "threat_of_new_entrants",
    "label": "Threat of new entrants",
    "guiding_question": "How easily could a new competitor enter this market?"
  },
  { "key": "supplier_power", "label": "Bargaining power of suppliers", "...": "..." },
  { "key": "buyer_power", "label": "Bargaining power of buyers", "...": "..." },
  { "key": "threat_of_substitutes", "label": "Threat of substitutes", "...": "..." },
  { "key": "competitive_rivalry", "label": "Competitive rivalry", "...": "..." }
]
```

**Input 2** — fill in two of the five sections and save:
```json
POST /problem-framing/analyses
{
  "title": "EU cloud market structure",
  "framework": "five_forces",
  "entries": {
    "competitive_rivalry": ["Three large incumbents dominate 70% of share"],
    "threat_of_new_entrants": ["High capital requirements limit new entry"]
  }
}
```
**Output:**
```json
{
  "analysis_id": "144a2a17-c44e-427a-bf54-74ae6edfc7a9",
  "title": "EU cloud market structure",
  "framework": "five_forces",
  "entries": { "...": "as submitted" },
  "completion_ratio": 0.4,
  "created_at": "2026-07-20T05:13:05.195837Z"
}
```
**What to check:** `completion_ratio` = 2/5 sections filled = `0.4`. The UI's progress badge
should read **40%**.

---

## 3. Evidence Research — `/dashboard/evidence-research`

**Input 1** — ingest a document:
```json
POST /evidence-research/documents
{
  "title": "Gartner Cloud Market 2026",
  "source_label": "Gartner 2026 report, p.14",
  "content": "Acquisition remains the fastest route to market share in the enterprise cloud segment. Competitors who acquired regional players saw a 23 percent faster time-to-revenue compared to organic build-out."
}
```
**Output:**
```json
{
  "document_id": "329987a2-ec0c-418d-8d3a-82061300e60c",
  "title": "Gartner Cloud Market 2026",
  "source_label": "Gartner 2026 report, p.14",
  "created_at": "2026-07-20T05:13:11.929430Z"
}
```

**Input 2** — search it:
```json
POST /evidence-research/search
{"query": "acquisition market share", "limit": 3}
```
**Output:**
```json
[
  {
    "document_id": "329987a2-ec0c-418d-8d3a-82061300e60c",
    "document_title": "Gartner Cloud Market 2026",
    "source_label": "Gartner 2026 report, p.14",
    "excerpt": "Acquisition remains the fastest route to market share in the enterprise cloud segment. Competitors who acquired regional…",
    "relevance_score": 0.2387
  }
]
```
**What to check:** the excerpt is verbatim (truncated with `…`, never paraphrased). Try
searching for a word that isn't in the document (e.g. `"blockchain"`) — expect an **empty
array**, not an error.

---

## 4. Financial Modeling — `/dashboard`

**Input** — a deliberately too-low discount rate to trigger a benchmark flag:
```json
POST /financial-modeling/cash-flow-models
{
  "project_name": "EU expansion",
  "currency": "USD",
  "discount_rate_percent": 2,
  "industry": "software",
  "cash_flows": [
    {"period": 0, "amount": "-1000000"},
    {"period": 1, "amount": "350000"},
    {"period": 2, "amount": "400000"},
    {"period": 3, "amount": "450000"},
    {"period": 4, "amount": "500000"}
  ]
}
```
**Output:**
```json
{
  "model_id": "43cb67cd-2470-4195-98a0-29e2a0fc6ae9",
  "npv": "613572.53",
  "irr_percent": "23.47345302790172570073303628",
  "payback_period": "2.555555555555555555555555556",
  "flags": [
    "The 2.0% discount rate is below the typical software range (8–11%). A discount rate that's too low overstates NPV — confirm the cost of capital used here."
  ]
}
```
**What to check:** the amber `FlagsCallout` renders under the valuation. Re-run with
`discount_rate_percent: 9` — expect `flags: []`.

**Input 2** — scenario comparison (Bear/Base/Bull), all three carrying probabilities:
```json
POST /financial-modeling/scenarios/evaluate
{
  "project_name": "EU expansion",
  "currency": "USD",
  "discount_rate_percent": 9,
  "scenarios": [
    {"name": "Bear", "probability_percent": 25, "cash_flows": [{"period":0,"amount":"-1000000"},{"period":1,"amount":"200000"},{"period":2,"amount":"250000"}]},
    {"name": "Base", "probability_percent": 50, "cash_flows": [{"period":0,"amount":"-1000000"},{"period":1,"amount":"350000"},{"period":2,"amount":"400000"}]},
    {"name": "Bull", "probability_percent": 25, "cash_flows": [{"period":0,"amount":"-1000000"},{"period":1,"amount":"500000"},{"period":2,"amount":"600000"}]}
  ]
}
```
**Output:**
```json
{
  "outcomes": [
    {"name": "Bear", "npv": "-606093.76", "irr_percent": "-39.01", "probability_percent": "25.00"},
    {"name": "Base", "npv": "-342227.09", "irr_percent": "-16.88", "probability_percent": "50.0"},
    {"name": "Bull", "npv": "-36276.41",  "irr_percent": "6.39",   "probability_percent": "25.00"}
  ],
  "probability_weighted_npv": "-331706.09"
}
```
**What to check:** `probability_weighted_npv` is the large, styled headline number — it should
equal `0.25×(-606093.76) + 0.5×(-342227.09) + 0.25×(-36276.41)`. All three scenarios are
negative here on purpose (only 2 periods of cash flow modeled) — a good example of the tool
correctly flagging a project that doesn't recover its investment yet.

---

## 5. Decision Analysis — `/dashboard/decision-analysis`

**Input** — MCDA ranking:
```json
POST /decision-analysis/mcda/rank
{
  "title": "Market entry approach",
  "criteria": [
    {"name": "cost", "weight": 0.4, "higher_is_better": false},
    {"name": "speed_to_market", "weight": 0.3, "higher_is_better": true},
    {"name": "strategic_fit", "weight": 0.3, "higher_is_better": true}
  ],
  "options": [
    {"name": "Build in-house", "scores": {"cost": 8, "speed_to_market": 3, "strategic_fit": 9}},
    {"name": "Acquire competitor", "scores": {"cost": 3, "speed_to_market": 9, "strategic_fit": 6}}
  ]
}
```
**Output:**
```json
{
  "analysis_id": "a9271d22-b832-4a5f-9fe4-13fc7d51a8b4",
  "rankings": [
    {"option": "Acquire competitor", "weighted_score": 0.7, "normalized_scores": {"cost": 1.0, "speed_to_market": 1.0, "strategic_fit": 0.0}},
    {"option": "Build in-house", "weighted_score": 0.3, "normalized_scores": {"cost": 0.0, "speed_to_market": 0.0, "strategic_fit": 1.0}}
  ],
  "recommended_option": "Acquire competitor",
  "weight_robustness": [
    {"criterion": "cost", "current_weight": 0.4, "flips_at_weight": null, "direction": "stable"},
    {"criterion": "speed_to_market", "current_weight": 0.3, "flips_at_weight": null, "direction": "stable"},
    {"criterion": "strategic_fit", "current_weight": 0.3, "flips_at_weight": 0.5, "direction": "increase"}
  ],
  "flags": []
}
```
**What to check:** `flips_at_weight: null` for `cost`/`speed_to_market` means the recommendation
is robust to reasonable disagreement about those weights. `strategic_fit` would flip the
recommendation if increased to `0.5` — that's the one weight worth debating.

**Decision Tree** — `/dashboard/decision-analysis/decision-tree`:
```json
POST /decision-analysis/decision-tree/evaluate
{
  "title": "Expand vs status quo",
  "options": [
    {"name": "Expand", "outcomes": [{"name":"high_demand","probability":0.5,"payoff":1000},{"name":"low_demand","probability":0.5,"payoff":-200}]},
    {"name": "Status quo", "outcomes": [{"name":"high_demand","probability":0.5,"payoff":100},{"name":"low_demand","probability":0.5,"payoff":100}]}
  ]
}
```
**Output:**
```json
{
  "recommended_option": "Expand",
  "expected_value_of_perfect_information": 150.0,
  "flags": ["The value of perfect information (EVPI = 150) is at least 30% of the best option's expected value. It may be worth commissioning more research or evidence before committing to this decision."],
  "probability_breakeven": {
    "outcome_name": "high_demand", "option_a": "Expand", "option_b": "Status quo",
    "breakeven_probability": 0.25
  }
}
```
**What to check:** `breakeven_probability: 0.25` means "Expand" wins as long as you believe
`high_demand` is more than 25% likely — well below the modeled 50%, so the recommendation has
real margin.

**Monte Carlo** — `/dashboard/decision-analysis/monte-carlo`:
```json
POST /decision-analysis/monte-carlo/run
{
  "title": "Revenue uncertainty",
  "variables": [{"name": "revenue", "kind": "normal", "params": [1000000, 100000]}],
  "fixed_costs": 800000,
  "iterations": 10000,
  "seed": 42
}
```
**Output (truncated):**
```json
{
  "mean": 198975.01,
  "std_dev": 100633.61,
  "percentile_5": 32590.65,
  "percentile_95": 364273.99,
  "probability_negative": 0.0233,
  "histogram": [ { "bin_start": -238911.46, "bin_end": -210861.66, "count": 1 }, "... 19 more bins" ]
}
```
**What to check:** re-run with the same `seed: 42` — every number must match exactly
(reproducibility is the whole point of requiring an explicit seed).

---

## 6. Recommendation Synthesis — `/dashboard/recommendation-synthesis`

**Input 1** — fuse the MCDA result with the evidence citation from Section 3:
```json
POST /recommendation-synthesis/rationales
{
  "title": "Market entry approach — final rationale",
  "quant_context": "decision_analysis",
  "quant_analysis_id": "a9271d22-b832-4a5f-9fe4-13fc7d51a8b4",
  "recommended_option": "Acquire competitor",
  "confidence_note": "MCDA weighted score margin of 0.4, driven mainly by speed-to-market.",
  "evidence_citations": [{
    "document_id": "329987a2-ec0c-418d-8d3a-82061300e60c",
    "document_title": "Gartner Cloud Market 2026",
    "source_label": "Gartner 2026 report, p.14",
    "excerpt": "Competitors who acquired regional players saw a 23 percent faster time-to-revenue.",
    "relevance_score": 0.24
  }]
}
```
**Output:** `current_recommendation` starts equal to `recommended_option` ("Acquire competitor"),
`overrides: []`.

**Input 2** — override it:
```json
POST /recommendation-synthesis/rationales/{id}/override
{
  "overridden_by": "jane.analyst",
  "reason": "EU regulatory scrutiny on cloud acquisitions not weighted in the MCDA model",
  "new_recommended_option": "Partner / JV"
}
```
**Output:**
```json
{
  "recommended_option": "Acquire competitor",
  "current_recommendation": "Partner / JV",
  "overrides": [{
    "overridden_by": "jane.analyst",
    "reason": "EU regulatory scrutiny on cloud acquisitions not weighted in the MCDA model",
    "new_recommended_option": "Partner / JV",
    "overridden_at": "2026-07-20T05:13:48.519217Z"
  }]
}
```
**What to check:** `recommended_option` (the original) is unchanged — overrides are additive,
never destructive. The detail page must show both the original and current recommendation
side by side.

**Input 3** — generate narrative (without a Groq key configured):
```
POST /recommendation-synthesis/rationales/{id}/narrative
```
**Output:** `HTTP 503`
```json
{"detail": "SDIE_GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys and put it in backend/.env"}
```
**What to check:** the frontend shows this exact message, not a generic error banner. Add a
free key to `backend/.env` and re-run to see actual generated prose instead.

**Input 4** — download the one-pager:
```
GET /recommendation-synthesis/rationales/{id}/one-pager
```
**Output:** `HTTP 200`, `Content-Type: application/pdf`, a real single-page PDF (~3.4KB) — the
"Download one-pager PDF" button should trigger a browser file download with this response.

---

## 7. Cross-cutting checks

- **Tenant isolation:** repeat any `GET` with a different `X-Tenant-Id` header — every list
  endpoint should come back empty; nothing created under tenant A is visible to tenant B.
- **Validation errors:** POST an MCDA request where criteria weights sum to `0.8` instead of
  `1.0` — expect `HTTP 422` with a detail message naming the actual sum.
- **Not-found handling:** `GET /decision-analysis/analyses/00000000-0000-0000-0000-000000000000`
  — expect `HTTP 404`, not a 500.
- **Workspace cross-context validation:** try linking a bogus ID —
  `POST /workspace/engagements/{id}/link-financial-model` with
  `{"model_id": "00000000-0000-0000-0000-000000000000"}` — expect `HTTP 404` with
  `"Financial model ... not found"`, proving the link endpoints actually check existence rather
  than blindly storing whatever ID they're given.

---

## 8. Full lifecycle recap (ties Sections 1–6 together)

Linking everything created above back to the Section 1 engagement, in whatever order (the
platform doesn't enforce a strict sequence):

```
POST /workspace/engagements/{eng_id}/link-problem-framing   {"analysis_id": "144a2a17-..."}
POST /workspace/engagements/{eng_id}/link-evidence           {"document_id": "329987a2-..."}
POST /workspace/engagements/{eng_id}/link-decision-analysis  {"analysis_id": "a9271d22-..."}
POST /workspace/engagements/{eng_id}/link-rationale           {"rationale_id": "eddcb58f-..."}
```

**Final state:**
```json
{
  "status": "complete",
  "problem_framing_analysis_id": "144a2a17-c44e-427a-bf54-74ae6edfc7a9",
  "evidence_document_ids": ["329987a2-ec0c-418d-8d3a-82061300e60c"],
  "financial_model_id": null,
  "decision_analysis_id": "a9271d22-b832-4a5f-9fe4-13fc7d51a8b4",
  "rationale_id": "eddcb58f-b992-4cc8-8ae8-818bd95595b5"
}
```
**What to check:** `status` reached `"complete"` because a rationale AND a quant analysis
(decision_analysis, in this case — financial_model_id is still null and that's fine, only one
of the two is required) are both linked. On the workspace detail page, all four linked stages
should show a green checkmark and a "View artifact" link.
