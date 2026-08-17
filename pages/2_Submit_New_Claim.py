from datetime import date, timedelta

import streamlit as st

from fraudshield import claude_client, data, ui

st.set_page_config(page_title="Submit New Claim | FraudShield", page_icon="🆕", layout="wide")
ui.inject_base_css()
st.title("🆕 Submit a New Claim")
st.caption(
    "Fill out a claim like a policyholder or intake system would. On submit, Claude reviews it "
    "live and returns a full fraud risk assessment in seconds."
)

LEGIT_EXAMPLE = {
    "claimant_name": "Rachel Kim",
    "claim_type": "Auto",
    "policy_start_date": date(2019, 3, 10),
    "incident_date": date.today() - timedelta(days=5),
    "reported_date": date.today() - timedelta(days=5),
    "incident_location": "Broadway & 4th St, Springfield",
    "incident_description": (
        "Rear-ended at a stoplight during the evening commute. The other driver admitted fault at "
        "the scene. A police report was filed and two independent witnesses gave statements."
    ),
    "claimed_amount": 3200,
    "prior_claims_last_3_years": 0,
    "police_report_filed": True,
    "witnesses": 2,
    "repair_shop": "Broadway Collision",
    "medical_provider": "",
    "legal_representation": "",
    "adjuster_notes": "",
}

SUSPICIOUS_EXAMPLE = {
    "claimant_name": "Kevin Brandt",
    "claim_type": "Auto",
    "policy_start_date": date.today() - timedelta(days=12),
    "incident_date": date.today() - timedelta(days=4),
    "reported_date": date.today() - timedelta(days=1),
    "incident_location": "Unlit stretch of Route 9, outside Springfield",
    "incident_description": (
        "Claims the vehicle was totaled in a single-car accident late at night. No police report "
        "was filed. The vehicle was towed directly to QuickFix Auto Body. Claimant is requesting a "
        "fast cash settlement instead of a repair."
    ),
    "claimed_amount": 24500,
    "prior_claims_last_3_years": 2,
    "police_report_filed": False,
    "witnesses": 0,
    "repair_shop": "QuickFix Auto Body",
    "medical_provider": "",
    "legal_representation": "",
    "adjuster_notes": "",
}


BLANK_TEMPLATE = {
    "claimant_name": "",
    "claim_type": "Auto",
    "policy_start_date": date.today(),
    "incident_date": date.today(),
    "reported_date": date.today(),
    "incident_location": "",
    "incident_description": "",
    "claimed_amount": 0,
    "prior_claims_last_3_years": 0,
    "police_report_filed": False,
    "witnesses": 0,
    "repair_shop": "",
    "medical_provider": "",
    "legal_representation": "",
    "adjuster_notes": "",
}


def apply_preset(preset: dict):
    for k, v in preset.items():
        st.session_state[f"f_{k}"] = v


st.markdown("**Quick-fill an example** (or fill out the form yourself below):")
p1, p2, p3 = st.columns(3)
p1.button("✅ Load a clean claim example", on_click=apply_preset, args=(LEGIT_EXAMPLE,), width="stretch")
p2.button("🚩 Load a suspicious claim example", on_click=apply_preset, args=(SUSPICIOUS_EXAMPLE,), width="stretch")
p3.button("🧹 Clear form", on_click=apply_preset, args=(BLANK_TEMPLATE,), width="stretch")

with st.form("new_claim_form"):
    c1, c2 = st.columns(2)
    with c1:
        claimant_name = st.text_input("Claimant name", key="f_claimant_name")
        claim_type = st.selectbox("Claim type", ["Auto", "Property", "Health", "Liability"], key="f_claim_type")
        policy_start_date = st.date_input("Policy start date", key="f_policy_start_date")
        incident_date = st.date_input("Incident date", key="f_incident_date")
        reported_date = st.date_input("Reported date", key="f_reported_date")
        incident_location = st.text_input("Incident location", key="f_incident_location")
    with c2:
        claimed_amount = st.number_input("Claimed amount ($)", min_value=0.0, step=100.0, key="f_claimed_amount")
        prior_claims_last_3_years = st.number_input(
            "Prior claims in last 3 years", min_value=0, step=1, key="f_prior_claims_last_3_years"
        )
        witnesses = st.number_input("Independent witnesses", min_value=0, step=1, key="f_witnesses")
        police_report_filed = st.checkbox("Police report filed", key="f_police_report_filed")
        repair_shop = st.text_input("Repair shop (if applicable)", key="f_repair_shop")
        medical_provider = st.text_input("Medical provider (if applicable)", key="f_medical_provider")
        legal_representation = st.text_input("Legal representation (if applicable)", key="f_legal_representation")

    incident_description = st.text_area("Incident description", height=120, key="f_incident_description")
    adjuster_notes = st.text_area("Adjuster notes (optional)", height=80, key="f_adjuster_notes")

    submitted = st.form_submit_button("🛡️ Submit & analyze with Claude", width="stretch")

if submitted:
    if not claimant_name or not incident_description:
        st.error("Claimant name and incident description are required.")
    else:
        claim_id = data.next_claim_id()
        claim = {
            "id": claim_id,
            "claim_number": claim_id,
            "policy_number": f"POL-{claim_id.split('-')[-1]}",
            "claimant_name": claimant_name,
            "claim_type": claim_type,
            "policy_start_date": str(policy_start_date),
            "incident_date": str(incident_date),
            "reported_date": str(reported_date),
            "incident_location": incident_location,
            "incident_description": incident_description,
            "claimed_amount": float(claimed_amount),
            "prior_claims_last_3_years": int(prior_claims_last_3_years),
            "police_report_filed": bool(police_report_filed),
            "witnesses": int(witnesses),
            "repair_shop": repair_shop or None,
            "medical_provider": medical_provider or None,
            "legal_representation": legal_representation or None,
            "adjuster_notes": adjuster_notes or None,
        }
        with st.spinner("Claude is reviewing the new claim..."):
            try:
                assessment = claude_client.analyze_claim(claim)
                data.append_submitted_claim(claim)
                data.update_cache_entry(claim_id, assessment)
                st.success(f"Claim {claim_id} submitted and analyzed.")
                st.divider()
                st.subheader(f"AI fraud assessment — {claim_id}")
                ui.render_assessment(assessment)
                st.page_link("pages/1_Claims_Dashboard.py", label="View this claim on the Claims Dashboard →")
            except RuntimeError as exc:
                st.error(str(exc))
