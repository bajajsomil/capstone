"""All interaction with the Gemini API for fraud analysis lives here.

Structured outputs are obtained via Gemini's controlled generation (a Pydantic
schema passed as response_schema), so every response is a validated object
rather than free text that needs parsing/guessing.
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Literal, Optional

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, Field

# gemini-flash-lite-latest: fast, cheap, and comfortably within the free-tier
# rate limits that the full "flash" preview models were hitting during testing.
MODEL = os.environ.get("FRAUDSHIELD_MODEL", "gemini-flash-lite-latest")

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to a .env file in the project "
                "root (copy .env.example to .env) or export it in your shell, then "
                "restart the app."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _generate_with_retry(max_attempts: int = 5, **kwargs):
    """Call generate_content, retrying on rate limits (429) and transient
    server overload (503) with backoff, since the free tier is bursty."""
    client = get_client()
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(**kwargs)
        except ClientError as exc:
            last_exc = exc
            if getattr(exc, "code", None) != 429 or attempt == max_attempts:
                raise RuntimeError(f"Gemini request failed: {exc}") from exc
            time.sleep(15 * attempt)
        except ServerError as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise RuntimeError(f"Gemini request failed after retries: {exc}") from exc
            time.sleep(3 * (2 ** (attempt - 1)))
    raise RuntimeError(f"Gemini request failed after retries: {last_exc}")


def _require_parsed(response):
    if response.parsed is None:
        raise RuntimeError(
            "Gemini returned a response that didn't match the expected schema. "
            f"Raw output: {response.text!r}"
        )
    return response.parsed


# ---------------------------------------------------------------------------
# Single-claim fraud risk assessment
# ---------------------------------------------------------------------------

class RedFlag(BaseModel):
    flag: str = Field(description="Short name of the fraud indicator, e.g. 'Early policy inception'.")
    severity: Literal["Low", "Medium", "High"]
    explanation: str = Field(description="1-2 sentences, grounded in the claim facts provided.")


class FraudAssessment(BaseModel):
    risk_score: int = Field(ge=0, le=100, description="0 (no indicators) to 100 (very high confidence of fraud).")
    risk_level: Literal["Low", "Medium", "High"]
    red_flags: list[RedFlag] = Field(description="Evidence-grounded fraud indicators found. Empty if none.")
    summary: str = Field(description="2-4 sentence plain-English summary for a claims adjuster.")
    recommended_action: Literal["Approve", "Request More Information", "Investigate", "Escalate to SIU"]
    confidence: float = Field(ge=0, le=1)


ASSESSMENT_SYSTEM_PROMPT = """You are FraudShield AI, a senior Special Investigations Unit (SIU) fraud \
analyst assisting claims adjusters at a property & casualty insurance carrier. You review individual \
claim files and produce calibrated, evidence-based fraud risk assessments.

Ground rules:
- Base every red flag strictly on facts present in the claim data you are given. Never invent details.
- Weigh mitigating evidence as heavily as suspicious signals: police reports, independent witnesses, \
consistent documentation, and a long clean policy history should lower risk, even for large claims.
- Consider known fraud indicator patterns, including: claims filed shortly after policy inception or a \
coverage increase; repair or medical costs inflated relative to typical costs for similar claims; delayed \
reporting; missing or inconsistent documentation; absence of independent witnesses or a police report \
where one would be expected; soft-tissue injury claims tied to a recurring network of the same clinic, \
attorney, or repair shop; high prior-claim frequency; inconsistent statements over time; and mismatches \
between described damage and supporting evidence such as photos.
- This assessment supports human decision-making. It does not make a final coverage or claim \
determination. Always recommend an action but defer final judgment to a human adjuster or investigator.
- Be fair to genuine policyholders. A severe accident or a large claim is not itself suspicious without \
supporting fraud indicators."""


def analyze_claim(claim: dict) -> dict:
    response = _generate_with_retry(
        model=MODEL,
        contents=(
            "Review the following claim file and produce a fraud risk assessment.\n\n"
            f"```json\n{json.dumps(claim, indent=2)}\n```"
        ),
        config=types.GenerateContentConfig(
            system_instruction=ASSESSMENT_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=FraudAssessment,
        ),
    )
    result = _require_parsed(response).model_dump()
    result["claim_id"] = claim.get("id")
    result["model"] = MODEL
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Cross-claim fraud ring / collusion detection
# ---------------------------------------------------------------------------

class RingCluster(BaseModel):
    cluster_name: str
    claim_ids: list[str]
    shared_entities: list[str] = Field(
        description="Shared repair shops, clinics, attorneys, addresses, or other linking entities."
    )
    risk_level: Literal["Low", "Medium", "High"]
    explanation: str


class RingFindings(BaseModel):
    clusters: list[RingCluster]
    overall_summary: str


RING_SYSTEM_PROMPT = """You are FraudShield AI's network analysis module. You are given a batch of \
insurance claims and must identify potential organized fraud rings or collusion clusters: groups of two \
or more claims linked by shared entities (repair shops, medical clinics, law firms, addresses, phone \
numbers) combined with a suspicious pattern (staged-looking accidents, recurring soft-tissue injury \
claims, inflated estimates, tight time clustering).

Rules:
- Only report a cluster when a real shared entity links the claims in the data provided. Do not \
speculate about claims that share no entity.
- A shared entity alone is not sufficient (e.g., two neighbors each filing an unrelated, well-documented \
claim is not a ring). Explain the combination of facts that makes the cluster suspicious, or omit it.
- It is fine to return zero clusters if none are credible."""


def detect_fraud_rings(claims: list) -> dict:
    response = _generate_with_retry(
        model=MODEL,
        contents=(
            "Analyze the following batch of claims for potential organized fraud rings.\n\n"
            f"```json\n{json.dumps(claims, indent=2)}\n```"
        ),
        config=types.GenerateContentConfig(
            system_instruction=RING_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RingFindings,
        ),
    )
    result = _require_parsed(response).model_dump()
    result["model"] = MODEL
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Adjuster Q&A chat about a specific claim
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """You are FraudShield AI, helping a claims adjuster review a specific insurance \
claim. You have the claim file and a prior fraud risk assessment as context. Answer the adjuster's \
questions concisely and only using the information provided; say so plainly if something isn't in the \
file rather than guessing. You are a decision-support tool, not the final decision-maker."""


def ask_about_claim(claim: dict, assessment: dict, question: str, history: Optional[list] = None) -> str:
    context = (
        f"Claim file:\n```json\n{json.dumps(claim, indent=2)}\n```\n\n"
        f"Prior fraud risk assessment:\n```json\n{json.dumps(assessment, indent=2)}\n```"
    )
    contents = [
        types.Content(role="user", parts=[types.Part(text=context)]),
        types.Content(
            role="model",
            parts=[types.Part(text="Understood, I have the claim file and the prior assessment. What would you like to know?")],
        ),
    ]
    for turn in history or []:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    response = _generate_with_retry(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT),
    )
    return response.text
