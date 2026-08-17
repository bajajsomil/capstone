"""One-time script to pre-generate Gemini fraud assessments for the seed claims,
so the dashboard loads instantly with real AI-generated content instead of
hitting the API on every page view.

Usage:
    python scripts/precompute_analysis.py

Requires GEMINI_API_KEY to be set, e.g. in a .env file in the project root.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from fraudshield import data, ai_client  # noqa: E402

# Light throttle between calls to stay comfortably under free-tier rate limits.
DELAY_BETWEEN_CALLS_SECONDS = 3


def main():
    claims = [c for c in data.load_claims() if not str(c["id"]).startswith("SUBMITTED")]
    cache = data.load_cache()
    for claim in claims:
        print(f"Analyzing {claim['id']} ({claim['claimant_name']})...", flush=True)
        try:
            assessment = ai_client.analyze_claim(claim)
            cache[claim["id"]] = assessment
            data.save_cache(cache)
            print(f"  -> {assessment['risk_level']} risk (score {assessment['risk_score']})", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! failed: {exc}", flush=True)
        time.sleep(DELAY_BETWEEN_CALLS_SECONDS)
    print(f"\nSaved {len(cache)} assessments to {data.CACHE_PATH}")

    print("\nRunning cross-claim fraud ring analysis...", flush=True)
    try:
        findings = ai_client.detect_fraud_rings(claims)
        data.save_ring_findings(findings)
        print(f"Found {len(findings.get('clusters', []))} cluster(s). Saved to {data.RING_CACHE_PATH}")
    except Exception as exc:  # noqa: BLE001
        print(f"  !! ring analysis failed: {exc}")


if __name__ == "__main__":
    main()
