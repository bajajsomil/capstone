"""Loading and caching of claim records and their fraud assessments."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLAIMS_PATH = BASE_DIR / "data" / "claims_seed.json"
CACHE_PATH = BASE_DIR / "data" / "analysis_cache.json"
NEW_CLAIMS_PATH = BASE_DIR / "data" / "submitted_claims.json"
RING_CACHE_PATH = BASE_DIR / "data" / "ring_findings.json"


def load_claims() -> list:
    with open(CLAIMS_PATH, "r", encoding="utf-8") as f:
        seed = json.load(f)
    return seed + load_submitted_claims()


def load_claim(claim_id: str):
    for claim in load_claims():
        if claim["id"] == claim_id:
            return claim
    return None


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def update_cache_entry(claim_id: str, assessment: dict) -> dict:
    cache = load_cache()
    cache[claim_id] = assessment
    save_cache(cache)
    return cache


def load_submitted_claims() -> list:
    if not NEW_CLAIMS_PATH.exists():
        return []
    with open(NEW_CLAIMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def append_submitted_claim(claim: dict) -> None:
    claims = load_submitted_claims()
    claims.append(claim)
    with open(NEW_CLAIMS_PATH, "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)


def load_ring_findings():
    if not RING_CACHE_PATH.exists():
        return None
    with open(RING_CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ring_findings(findings: dict) -> None:
    with open(RING_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)


def next_claim_id() -> str:
    existing = load_claims()
    numbers = []
    for c in existing:
        try:
            numbers.append(int(str(c["id"]).split("-")[-1]))
        except ValueError:
            continue
    next_n = (max(numbers) + 1) if numbers else 1001
    return f"CLM-{next_n}"
