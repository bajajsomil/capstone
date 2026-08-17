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
        ("3. Score & explain", "A calibrated 0–100 risk score, a risk tier, and specific red flags are returned as structured data, not a black box."),
        ("4. Decide", "A human adjuster reviews the recommendation — Approve, Request Info, Investigate, or Escalate to SIU — and makes the final call."),
    ]
    cols = st.columns(4)
    for col, (title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"**{title}**")
            st.caption(desc)

with right:
    st.subheader("Why it matters")
    st.metric("Illustrative loss ratio impact", "−15 to −25%", help="Directional estimate based on industry SIU benchmarks for AI-assisted triage; not a guarantee.")
    st.metric("Faster processing for genuine claims", "Minutes, not days", help="Low-risk claims can be fast-tracked instead of sitting in a generic review queue.")
    st.metric("Also catches", "Organized fraud rings", help="Cross-claim network analysis links claims sharing repair shops, clinics, attorneys, or addresses.")
    st.info("This is a proof-of-concept: illustrative figures above are directional, not measured production results.", icon="ℹ️")

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
