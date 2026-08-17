# 🛡️ FraudShield — AI-Powered Insurance Claims Fraud Detection

**Capstone Project — AI Practitioner+ Program (Claude)**

FraudShield is a proof-of-concept fraud detection and prevention tool for insurance claims. It uses
Claude as an always-on Special Investigations Unit (SIU) analyst that reviews every claim the moment
it's filed, scores its fraud risk with specific, evidence-grounded reasoning, and recommends a next
action — so genuine claims move fast and suspicious ones get routed to investigation immediately.

## The business problem

Fraud is one of the fastest-growing loss drivers in insurance, amplified by digital channels, staged
accidents, inflated repair bills, identity abuse, and organized fraud rings. Traditional rule-based
checks alone are insufficient and reactive: they catch yesterday's fraud patterns while adding friction
for the vast majority of genuine policyholders. FraudShield aims to provide proactive fraud prevention,
lower loss ratios, reduced investigation cost, and improved claims integrity — while keeping processing
fast and frictionless for legitimate claims.

## What it does

| Feature | Description |
|---|---|
| **Claims Dashboard** | KPI overview, risk distribution and claimed-amount charts, a filterable/searchable claims table, and a drill-down view per claim with the full AI assessment. |
| **Live claim analysis** | Every claim gets a 0–100 risk score, a risk tier (Low/Medium/High), specific red flags with severity and explanation, a recommended action (Approve / Request More Info / Investigate / Escalate to SIU), and a confidence level — all as structured, auditable output, not free-text guesswork. |
| **Submit a New Claim** | A live demo path: fill out a claim (or one-click a "clean" or "suspicious" example) and get an instant Claude-generated risk assessment. |
| **Fraud Ring Detection** | A network-analysis pass across the entire claims book that surfaces claims linked by shared repair shops, clinics, attorneys, or addresses — the pattern behind organized/staged-accident fraud rings — that no single-claim review would catch. |
| **Ask FraudShield** | A claim-scoped chat so an adjuster can ask follow-up questions ("why wasn't X a bigger factor?") and get an answer grounded in that claim's file and assessment. |

Every recommendation is explicitly framed as **decision support**, not a final determination — a human
adjuster or investigator always makes the call. This is stated directly to Claude in the system prompt.

## Why Claude, and how it's used

Rule engines can only catch fraud patterns someone already thought to encode. FraudShield instead gives
Claude the full claim narrative and asks it to reason the way a senior investigator would — weighing
red flags *against* mitigating evidence (police reports, witnesses, policy tenure) rather than just
pattern-matching keywords. Two design choices make this reliable enough to build a product on:

- **Forced tool use for structured output.** Every analysis call defines a JSON schema (`submit_fraud_assessment`
  / `submit_fraud_ring_findings`) and forces Claude to respond only via that tool. The app never parses
  free text — it gets a validated object back every time. See [`fraudshield/claude_client.py`](fraudshield/claude_client.py).
- **Grounding rules in the system prompt.** Claude is explicitly told to base every red flag only on facts
  present in the claim, to weigh mitigating evidence as heavily as suspicious signals, and to avoid
  penalizing legitimate claimants for circumstances outside their control (e.g., a severe accident is not
  itself suspicious).

## Architecture

```
Home.py                        Landing page / business case
pages/1_Claims_Dashboard.py    KPIs, charts, filterable table, claim drill-down + chat
pages/2_Submit_New_Claim.py    Live claim intake -> instant Claude analysis
pages/3_Fraud_Ring_Detection.py Cross-claim network analysis
fraudshield/
  claude_client.py             All Claude API calls, tool schemas, system prompts
  data.py                      Loading/caching of claims and assessments (JSON files)
  ui.py                        Shared styling, badges, colors, chart-safe palette
data/
  claims_seed.json             18 synthetic claims (mix of clean, ambiguous, and fraud-ring cases)
  analysis_cache.json          Pre-computed Claude assessments for the seed claims (generated once,
                                so the dashboard loads instantly without live API calls on every view)
  ring_findings.json           Pre-computed fraud-ring analysis for the seed claims
scripts/precompute_analysis.py One-time script that (re)generates the two cache files above
```

**Stack:** Python + [Streamlit](https://streamlit.io) (no separate frontend build step — this machine
didn't have Node.js available, and Streamlit gets a working, presentable UI shipped in a single day) +
the official `anthropic` SDK. Claim and assessment data are plain JSON files — no database needed for a
proof of concept at this scale.

## Setup

1. **Requirements:** Python 3.10+.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure your API key:
   ```
   copy .env.example .env
   ```
   then edit `.env` and set `ANTHROPIC_API_KEY=sk-ant-...`.
4. *(Optional but recommended)* Pre-generate assessments for the seed claims so the dashboard and fraud
   ring page load with real AI output immediately, instead of showing "not analyzed":
   ```
   python scripts/precompute_analysis.py
   ```
5. Run the app:
   ```
   python -m streamlit run Home.py
   ```
   Streamlit will open the app at `http://localhost:8501`.

Live features (the "Run live AI analysis" buttons, **Submit a New Claim**, and **Fraud Ring Detection**)
require a valid `ANTHROPIC_API_KEY`; without one, the sidebar shows a warning and those actions display a
friendly error instead of crashing.

## Suggested demo flow

1. **Home** — business framing: the problem, how the pipeline works, illustrative impact.
2. **Claims Dashboard** — show the KPI row and charts, then open a clean low-risk claim (e.g. `CLM-1007`)
   and a high-risk one (e.g. `CLM-1003` or `CLM-1018`) to contrast the reasoning and red flags.
3. **Submit a New Claim** — click "Load a suspicious claim example" (or type your own) and submit live,
   so the audience watches Claude generate a real assessment in seconds.
4. **Fraud Ring Detection** — run the live network analysis and show the claim cluster tied to
   *QuickFix Auto Body* / *Riverside Wellness & Rehab* / *Marcus Webb, Esq.* across multiple claimants —
   a pattern no single-claim review would surface.

## Responsible use & limitations

This is an MVP built for a one-day capstone, not a production underwriting system:

- All claim and claimant data in `data/claims_seed.json` is **synthetic**, invented for this demo.
- Risk scores are decision-support signals for a human adjuster, not automated denials or approvals.
- The business-impact figures on the Home page are **illustrative** industry-benchmark estimates, not
  measured results from a production deployment.
- A real deployment would need: integration with a real claims/policy system, document and photo
  verification, an audit trail and human-review workflow, bias/fairness testing across protected classes,
  and a proper database instead of flat JSON files.

## Roadmap (beyond this MVP)

- Photo/document analysis (e.g., damage photos vs. claimed repair scope) using Claude's vision input.
- A real fraud-indicator rules layer feeding structured signals into the prompt alongside the narrative.
- Case management integration (assign to an SIU investigator, track outcomes, feed back into prompts).
- Persistent storage (a real database) and authentication/roles (adjuster vs. SIU vs. admin).
