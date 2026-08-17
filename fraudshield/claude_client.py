"""All interaction with the Claude API for fraud analysis lives here.

Structured outputs are obtained via forced tool use, so every response is a
validated JSON object rather than free text that needs parsing/guessing.
"""
import json
import os
from datetime import datetime, timezone

from anthropic import Anthropic

MODEL = os.environ.get("FRAUDSHIELD_MODEL", "claude-sonnet-5")

_client = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to a .env file in the project "
                "root (copy .env.example to .env) or export it in your shell, then "
                "restart the app."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def _extract_tool_input(message, tool_name: str) -> dict:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return dict(block.input)
    raise RuntimeError(f"Claude did not return the expected '{tool_name}' tool call.")


# ---------------------------------------------------------------------------
# Single-claim fraud risk assessment
# ---------------------------------------------------------------------------

ASSESSMENT_TOOL = {
    "name": "submit_fraud_assessment",
    "description": "Submit a structured, evidence-based fraud risk assessment for a single insurance claim.",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Overall fraud risk, 0 (no indicators) to 100 (very high confidence of fraud).",
            },
            "risk_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
            "red_flags": {
                "type": "array",
                "description": "Specific, evidence-grounded fraud indicators found in the claim. Empty if none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "flag": {"type": "string", "description": "Short name, e.g. 'Early policy inception'."},
                        "severity": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "explanation": {"type": "string", "description": "1-2 sentences, grounded in the claim facts."},
                    },
                    "required": ["flag", "severity", "explanation"],
                },
            },
            "summary": {
                "type": "string",
                "description": "2-4 sentence plain-English summary of the assessment for a claims adjuster.",
            },
            "recommended_action": {
                "type": "string",
                "enum": ["Approve", "Request More Information", "Investigate", "Escalate to SIU"],
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["risk_score", "risk_level", "red_flags", "summary", "recommended_action", "confidence"],
    },
}

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
supporting fraud indicators.

Respond only by calling the submit_fraud_assessment tool."""


def analyze_claim(claim: dict) -> dict:
    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=ASSESSMENT_SYSTEM_PROMPT,
        tools=[ASSESSMENT_TOOL],
        tool_choice={"type": "tool", "name": "submit_fraud_assessment"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Review the following claim file and submit a fraud risk assessment.\n\n"
                    f"```json\n{json.dumps(claim, indent=2)}\n```"
                ),
            }
        ],
    )
    result = _extract_tool_input(message, "submit_fraud_assessment")
    result["claim_id"] = claim.get("id")
    result["model"] = MODEL
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Cross-claim fraud ring / collusion detection
# ---------------------------------------------------------------------------

RING_TOOL = {
    "name": "submit_fraud_ring_findings",
    "description": "Submit findings on potential organized fraud rings or collusion clusters detected across a batch of claims.",
    "input_schema": {
        "type": "object",
        "properties": {
            "clusters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cluster_name": {"type": "string"},
                        "claim_ids": {"type": "array", "items": {"type": "string"}},
                        "shared_entities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Shared repair shops, clinics, attorneys, addresses, or other linking entities.",
                        },
                        "risk_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "explanation": {"type": "string"},
                    },
                    "required": ["cluster_name", "claim_ids", "shared_entities", "risk_level", "explanation"],
                },
            },
            "overall_summary": {"type": "string"},
        },
        "required": ["clusters", "overall_summary"],
    },
}

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
- It is fine to return zero clusters if none are credible.

Respond only by calling the submit_fraud_ring_findings tool."""


def detect_fraud_rings(claims: list) -> dict:
    client = get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=RING_SYSTEM_PROMPT,
        tools=[RING_TOOL],
        tool_choice={"type": "tool", "name": "submit_fraud_ring_findings"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Analyze the following batch of claims for potential organized fraud rings.\n\n"
                    f"```json\n{json.dumps(claims, indent=2)}\n```"
                ),
            }
        ],
    )
    result = _extract_tool_input(message, "submit_fraud_ring_findings")
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


def ask_about_claim(claim: dict, assessment: dict, question: str, history: list = None) -> str:
    client = get_client()
    context = (
        f"Claim file:\n```json\n{json.dumps(claim, indent=2)}\n```\n\n"
        f"Prior fraud risk assessment:\n```json\n{json.dumps(assessment, indent=2)}\n```"
    )
    messages = [
        {"role": "user", "content": context},
        {
            "role": "assistant",
            "content": "Understood, I have the claim file and the prior assessment. What would you like to know?",
        },
    ]
    for turn in history or []:
        messages.append(turn)
    messages.append({"role": "user", "content": question})

    message = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=CHAT_SYSTEM_PROMPT,
        messages=messages,
    )
    return "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
