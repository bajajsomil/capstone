# FraudShield Evaluation Results

Ground truth (`evaluation_cases.json`) reflects the design intent behind the synthetic seed claims, authored by the same person who built the dataset - not independent third-party labeling. Treat this as a sanity check on a small synthetic set, not a production benchmark.

Evaluation set: 18 synthetic claims

## Structured output validity

- Valid against the `FraudAssessment` Pydantic schema: 18/18

## Risk-tier agreement

- Exact tier match: 16/18 (88.9%)
- Mismatches, reported rather than tuned away (2):

| Claim | Expected | Actual | Score | Note |
|---|---|---|---|---|
| CLM-1009 | High | Medium | 58 | Delayed theft report, no telematics data, noted financial distress. |
| CLM-1014 | High | Medium | 68 | Unusually high visit frequency at a newly opened clinic, adjuster-flagged upcoding pattern. |

## Fraud ring detection

- Expected ring members: ['CLM-1003', 'CLM-1004', 'CLM-1005', 'CLM-1006', 'CLM-1016', 'CLM-1018']
- Flagged by the model: ['CLM-1003', 'CLM-1004', 'CLM-1005', 'CLM-1006', 'CLM-1016', 'CLM-1018']
- True positives: 6/6
- False positives (flagged but shouldn't be): none
- False negatives (missed): none
- Precision: 100% · Recall: 100% · F1: 100%
  (on 6 expected ring members in an 18-claim synthetic set - a sanity check, not a statistically meaningful sample)
- Notably, CLM-1008 and CLM-1013 share an address but were correctly **not** flagged as a ring - a deliberate trap case for over-flagging on coincidental overlap.
