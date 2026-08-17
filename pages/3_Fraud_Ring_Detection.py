import pandas as pd
import streamlit as st

from fraudshield import ai_client, data, ui

st.set_page_config(page_title="Fraud Ring Detection | FraudShield", page_icon="🕸️", layout="wide")
ui.inject_base_css()
st.title("🕸️ Fraud Ring Detection")
st.caption(
    "Individual claims can each look only mildly suspicious on their own. Here Gemini reviews the "
    "entire claims book at once, looking for claims linked by shared repair shops, clinics, "
    "attorneys, or addresses that together suggest an organized or collusive fraud ring."
)

claims = data.load_claims()
findings = data.load_ring_findings()

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Run live network analysis", width="stretch"):
        with st.spinner(f"Gemini is cross-referencing {len(claims)} claims for shared entities..."):
            try:
                findings = ai_client.detect_fraud_rings(claims)
                data.save_ring_findings(findings)
            except RuntimeError as exc:
                st.error(str(exc))

if not findings:
    st.info("No network analysis has been run yet. Click **Run live network analysis** to get started.")
else:
    st.write(findings.get("overall_summary", ""))
    clusters = findings.get("clusters", [])
    if not clusters:
        st.success("No credible fraud rings identified in the current claims book.")
    for cluster in clusters:
        with st.container(border=True):
            top = st.columns([4, 1])
            with top[0]:
                st.markdown(f"#### {cluster['cluster_name']}")
            with top[1]:
                st.markdown(ui.risk_badge_html(cluster["risk_level"]), unsafe_allow_html=True)
            st.write(cluster["explanation"])
            if cluster.get("shared_entities"):
                st.markdown("**Shared entities:** " + ", ".join(cluster["shared_entities"]))
            member_claims = [data.load_claim(cid) for cid in cluster.get("claim_ids", [])]
            member_claims = [c for c in member_claims if c]
            if member_claims:
                st.markdown("**Claims involved:**")
                mdf = pd.DataFrame(
                    [
                        {
                            "Claim ID": c["id"],
                            "Claimant": c["claimant_name"],
                            "Type": c["claim_type"],
                            "Amount": ui.fmt_currency(c["claimed_amount"]),
                            "Reported": c["reported_date"],
                        }
                        for c in member_claims
                    ]
                )
                st.dataframe(mdf, width="stretch", hide_index=True)
    st.caption(f"Analysis generated {findings.get('generated_at', '')} · model {findings.get('model', '')}")
