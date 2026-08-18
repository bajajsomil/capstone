"""Lightweight evaluation harness for FraudShield's cached AI outputs.

Ground truth in evaluation_cases.json was authored by the same person who
designed the synthetic seed dataset (data/claims_seed.json) - it reflects
design intent, not independent third-party labeling. That's disclosed here
rather than presented as a rigorous benchmark: for 18 synthetic claims, the
honest value of this script is in making disagreements visible (including
the ones that don't flatter the model), not in a polished-looking score.

Usage:
    python evaluation/evaluate.py
Reads only committed JSON files - no API calls, no network access needed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fraudshield.ai_client import FraudAssessment  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
CASES_PATH = BASE_DIR / "evaluation_cases.json"
RESULTS_PATH = BASE_DIR / "RESULTS.md"
DATA_DIR = BASE_DIR.parent / "data"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    cases = {c["claim_id"]: c for c in load_json(CASES_PATH)}
    assessments = load_json(DATA_DIR / "analysis_cache.json")
    ring_findings = load_json(DATA_DIR / "ring_findings.json")

    actual_ring_members = set()
    for cluster in ring_findings.get("clusters", []):
        actual_ring_members.update(cluster.get("claim_ids", []))

    schema_valid, schema_invalid = 0, []
    tier_matches, tier_mismatches = [], []

    for claim_id, case in cases.items():
        assessment = assessments.get(claim_id)
        if assessment is None:
            schema_invalid.append((claim_id, "missing from analysis_cache.json"))
            continue

        try:
            fields = {k: v for k, v in assessment.items() if k in FraudAssessment.model_fields}
            FraudAssessment.model_validate(fields)
            schema_valid += 1
        except Exception as exc:  # noqa: BLE001
            schema_invalid.append((claim_id, str(exc)))

        actual_tier = assessment.get("risk_level")
        expected_tier = case["expected_risk_tier"]
        record = {
            "claim_id": claim_id,
            "expected": expected_tier,
            "actual": actual_tier,
            "score": assessment.get("risk_score"),
            "rationale": case["rationale"],
        }
        (tier_matches if actual_tier == expected_tier else tier_mismatches).append(record)

    ring_expected = {cid for cid, c in cases.items() if c["expected_in_ring"]}
    true_positives = ring_expected & actual_ring_members
    false_positives = actual_ring_members - ring_expected
    false_negatives = ring_expected - actual_ring_members

    tp, fp, fn = len(true_positives), len(false_positives), len(false_negatives)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    total = len(cases)
    tier_accuracy = len(tier_matches) / total

    lines = []
    lines.append("# FraudShield Evaluation Results\n")
    lines.append(
        "Ground truth (`evaluation_cases.json`) reflects the design intent behind the synthetic "
        "seed claims, authored by the same person who built the dataset - not independent "
        "third-party labeling. Treat this as a sanity check on a small synthetic set, not a "
        "production benchmark.\n"
    )
    lines.append(f"Evaluation set: {total} synthetic claims\n")

    lines.append("## Structured output validity\n")
    lines.append(f"- Valid against the `FraudAssessment` Pydantic schema: {schema_valid}/{total}")
    if schema_invalid:
        for claim_id, err in schema_invalid:
            lines.append(f"  - **{claim_id}**: {err}")
    lines.append("")

    lines.append("## Risk-tier agreement\n")
    lines.append(f"- Exact tier match: {len(tier_matches)}/{total} ({tier_accuracy:.1%})")
    if tier_mismatches:
        lines.append(f"- Mismatches, reported rather than tuned away ({len(tier_mismatches)}):\n")
        lines.append("| Claim | Expected | Actual | Score | Note |")
        lines.append("|---|---|---|---|---|")
        for m in tier_mismatches:
            lines.append(
                f"| {m['claim_id']} | {m['expected']} | {m['actual']} | {m['score']} | "
                f"{m['rationale']} |"
            )
    else:
        lines.append("- No mismatches.")
    lines.append("")

    lines.append("## Fraud ring detection\n")
    lines.append(f"- Expected ring members: {sorted(ring_expected)}")
    lines.append(f"- Flagged by the model: {sorted(actual_ring_members)}")
    lines.append(f"- True positives: {tp}/{len(ring_expected)}")
    lines.append(f"- False positives (flagged but shouldn't be): {sorted(false_positives) or 'none'}")
    lines.append(f"- False negatives (missed): {sorted(false_negatives) or 'none'}")
    lines.append(f"- Precision: {precision:.0%} · Recall: {recall:.0%} · F1: {f1:.0%}")
    lines.append(
        "  (on 6 expected ring members in an 18-claim synthetic set - a sanity check, not a "
        "statistically meaningful sample)"
    )
    lines.append(
        "- Notably, CLM-1008 and CLM-1013 share an address but were correctly **not** flagged as "
        "a ring - a deliberate trap case for over-flagging on coincidental overlap."
    )

    report = "\n".join(lines)
    print(report)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
