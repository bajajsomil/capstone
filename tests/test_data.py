import json

import pytest

from fraudshield import data


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    claims_path = tmp_path / "claims_seed.json"
    seed = [
        {"id": "CLM-1001", "claimant_name": "Alice"},
        {"id": "CLM-1002", "claimant_name": "Bob"},
    ]
    claims_path.write_text(json.dumps(seed))

    monkeypatch.setattr(data, "CLAIMS_PATH", claims_path)
    monkeypatch.setattr(data, "CACHE_PATH", tmp_path / "analysis_cache.json")
    monkeypatch.setattr(data, "NEW_CLAIMS_PATH", tmp_path / "submitted_claims.json")
    monkeypatch.setattr(data, "RING_CACHE_PATH", tmp_path / "ring_findings.json")
    return seed


def test_load_claims_returns_seed(isolated_paths):
    assert [c["id"] for c in data.load_claims()] == ["CLM-1001", "CLM-1002"]


def test_load_claim_finds_by_id(isolated_paths):
    assert data.load_claim("CLM-1002")["claimant_name"] == "Bob"


def test_load_claim_missing_returns_none(isolated_paths):
    assert data.load_claim("CLM-9999") is None


def test_cache_starts_empty_and_round_trips(isolated_paths):
    assert data.load_cache() == {}
    data.update_cache_entry("CLM-1001", {"risk_level": "Low"})
    assert data.load_cache() == {"CLM-1001": {"risk_level": "Low"}}


def test_cache_update_preserves_other_entries(isolated_paths):
    data.update_cache_entry("CLM-1001", {"risk_level": "Low"})
    data.update_cache_entry("CLM-1002", {"risk_level": "High"})
    cache = data.load_cache()
    assert cache["CLM-1001"]["risk_level"] == "Low"
    assert cache["CLM-1002"]["risk_level"] == "High"


def test_submitted_claims_start_empty(isolated_paths):
    assert data.load_submitted_claims() == []


def test_next_claim_id_continues_from_seed(isolated_paths):
    assert data.next_claim_id() == "CLM-1003"


def test_append_submitted_claim_is_visible_in_load_claims(isolated_paths):
    data.append_submitted_claim({"id": "CLM-1003", "claimant_name": "Carol"})
    claims = data.load_claims()
    assert [c["id"] for c in claims] == ["CLM-1001", "CLM-1002", "CLM-1003"]
    assert data.load_claim("CLM-1003")["claimant_name"] == "Carol"


def test_next_claim_id_accounts_for_submitted_claims(isolated_paths):
    data.append_submitted_claim({"id": "CLM-1003", "claimant_name": "Carol"})
    assert data.next_claim_id() == "CLM-1004"


def test_ring_findings_absent_by_default(isolated_paths):
    assert data.load_ring_findings() is None


def test_ring_findings_round_trip(isolated_paths):
    findings = {"clusters": [], "overall_summary": "none found"}
    data.save_ring_findings(findings)
    assert data.load_ring_findings() == findings
