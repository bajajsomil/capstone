import streamlit as st

from fraudshield import ui

st.set_page_config(page_title="FraudShield | AI Claims Fraud Detection", page_icon="🛡️", layout="wide")
ui.inject_base_css()

st.markdown(
    """
    <div class="fs-hero">
        <h1>🛡️ FraudShield</h1>
        <p>Proactive, explainable fraud detection for insurance claims — powered by Gemini.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("The problem")
    st.write(
        "Fraud is one of the fastest-growing loss drivers in insurance, amplified by digital "
        "channels, staged accidents, inflated repair bills, identity abuse, and organized fraud "
        "rings. Traditional rule-based checks alone are insufficient and reactive — they catch "
        "yesterday's fraud patterns while today's more sophisticated schemes slip through, and "
        "they routinely add friction for genuine policyholders."
    )
    st.subheader("What FraudShield does")
    st.write(
        "FraudShield reviews every claim the moment it's filed, using Gemini as a tireless SIU "
        "analyst that reasons over the full claim narrative — not just a checklist of rules. "
        "Every score comes with **specific, evidence-grounded red flags** and a **recommended "
        "action**, so adjusters can approve genuine claims fast and route suspicious ones to "
        "investigation immediately."
    )

    st.markdown("##### How it works")
    steps = [
        ("1. Ingest", "A new or existing claim's facts, history, and documentation notes are structured for review."),
        ("2. Reason", "Gemini weighs fraud indicators against mitigating evidence — police reports, witnesses, tenure — the way a senior investigator would."),
        ("3. Score & explain", "A 0–100 risk score, a risk tier, and specific red flags are returned as structured data, not a black box."),
        ("4. Decide", "A human adjuster reviews the recommendation — Approve, Request Info, Investigate, or Escalate to SIU — and makes the final call."),
    ]
    cols = st.columns(4)
    for col, (title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"**{title}**")
            st.caption(desc)

with right:
    st.subheader("Evidence-backed prototype results")
    m1, m2 = st.columns(2)
    m1.metric("Schema validity", "18/18", help="Every cached assessment validates against the FraudAssessment Pydantic schema.")
    m2.metric("Risk-tier agreement", "16/18", help="88.9% exact agreement against a self-authored ground truth over 18 synthetic claims.")
    m3, m4 = st.columns(2)
    m3.metric("Ring members found", "6/6", help="Zero false positives, zero false negatives — including a deliberate shared-address trap case.")
    m4.metric("Tests passing", "27/27", help="Unit tests against a mocked Gemini client: persistence, formatting, retry/backoff, response validation.")
    st.caption(
        "From 18 synthetic claims and a self-authored ground truth — a sanity check, not a "
        "production benchmark. Full methodology and the two disclosed disagreements in "
        "[evaluation/RESULTS.md](https://github.com/bajajsomil/capstone/blob/main/evaluation/RESULTS.md)."
    )

    st.markdown("##### Responsible AI by design")
    st.markdown(
        "🛡️ **Human decision required** — the model recommends an action, a person decides.\n\n"
        "📋 **Evidence-grounded red flags** — grounded only in facts present in the claim file.\n\n"
        "🧩 **Structured schema validation** — every response is Pydantic-validated, never parsed free text.\n\n"
        "🔄 **Explicit failure handling** — API errors retry with backoff, then fail loudly, never silently.\n\n"
        "🧪 **Evaluated against known cases** — including a deliberate over-flagging trap case."
    )

st.divider()
st.subheader("Explore the prototype")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/1_Claims_Dashboard.py", label="📋 Claims Dashboard", help="Review triaged claims, risk scores, and red flags")
with c2:
    st.page_link("pages/2_Submit_New_Claim.py", label="🆕 Submit a New Claim", help="Live demo: submit a claim and get an instant AI risk assessment")
with c3:
    st.page_link("pages/3_Fraud_Ring_Detection.py", label="🕸️ Fraud Ring Detection", help="Cross-claim analysis to surface organized fraud networks")

with st.sidebar:
    st.caption("FraudShield MVP · built on the Gemini API")
    import os
    if os.environ.get("GEMINI_API_KEY"):
        st.success("Gemini API key detected", icon="✅")
    else:
        st.warning("No GEMINI_API_KEY found — set it in a .env file to enable live analysis.", icon="⚠️")
