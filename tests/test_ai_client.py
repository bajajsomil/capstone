from unittest.mock import MagicMock

import pytest
from google.genai.errors import ClientError, ServerError

from fraudshield import ai_client


class FakeParsed:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return dict(self._payload)


class FakeResponse:
    def __init__(self, parsed=None, text=""):
        self.parsed = parsed
        self.text = text


@pytest.fixture(autouse=True)
def no_real_sleeping(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)


def test_generate_with_retry_recovers_from_rate_limit(monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        ClientError(429, {"error": {"message": "rate limited"}}),
        FakeResponse(text="ok"),
    ]
    monkeypatch.setattr(ai_client, "get_client", lambda: fake_client)

    response = ai_client._generate_with_retry(model="x", contents="y")

    assert response.text == "ok"
    assert fake_client.models.generate_content.call_count == 2


def test_generate_with_retry_recovers_from_server_overload(monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        ServerError(503, {"error": {"message": "overloaded"}}),
        ServerError(503, {"error": {"message": "overloaded"}}),
        FakeResponse(text="ok"),
    ]
    monkeypatch.setattr(ai_client, "get_client", lambda: fake_client)

    response = ai_client._generate_with_retry(model="x", contents="y")

    assert response.text == "ok"
    assert fake_client.models.generate_content.call_count == 3


def test_generate_with_retry_gives_up_after_max_attempts(monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = ServerError(
        503, {"error": {"message": "still overloaded"}}
    )
    monkeypatch.setattr(ai_client, "get_client", lambda: fake_client)

    with pytest.raises(RuntimeError, match="failed after retries"):
        ai_client._generate_with_retry(model="x", contents="y", max_attempts=2)

    assert fake_client.models.generate_content.call_count == 2


def test_generate_with_retry_does_not_retry_non_rate_limit_client_errors(monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = ClientError(
        404, {"error": {"message": "model not found"}}
    )
    monkeypatch.setattr(ai_client, "get_client", lambda: fake_client)

    with pytest.raises(RuntimeError, match="Gemini request failed"):
        ai_client._generate_with_retry(model="x", contents="y")

    # a genuine 4xx like "model not found" won't fix itself on retry
    assert fake_client.models.generate_content.call_count == 1


def test_require_parsed_raises_with_raw_text_on_none():
    with pytest.raises(RuntimeError, match="didn't match the expected schema"):
        ai_client._require_parsed(FakeResponse(parsed=None, text="not valid json"))


def test_require_parsed_returns_value_when_present():
    parsed = FakeParsed({"risk_score": 5})
    assert ai_client._require_parsed(FakeResponse(parsed=parsed)) is parsed


def test_analyze_claim_attaches_claim_metadata(monkeypatch):
    fake_parsed = FakeParsed({"risk_score": 10, "risk_level": "Low"})
    monkeypatch.setattr(
        ai_client, "_generate_with_retry", lambda **kwargs: FakeResponse(parsed=fake_parsed)
    )

    result = ai_client.analyze_claim({"id": "CLM-1", "claimant_name": "Test"})

    assert result["risk_score"] == 10
    assert result["claim_id"] == "CLM-1"
    assert result["model"] == ai_client.MODEL
    assert "generated_at" in result


def test_detect_fraud_rings_attaches_model_metadata(monkeypatch):
    fake_parsed = FakeParsed({"clusters": [], "overall_summary": "none"})
    monkeypatch.setattr(
        ai_client, "_generate_with_retry", lambda **kwargs: FakeResponse(parsed=fake_parsed)
    )

    result = ai_client.detect_fraud_rings([{"id": "CLM-1"}])

    assert result["clusters"] == []
    assert result["model"] == ai_client.MODEL
    assert "generated_at" in result
