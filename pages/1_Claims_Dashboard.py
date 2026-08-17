import altair as alt
import pandas as pd
import streamlit as st

from fraudshield import claude_client, data, ui

st.set_page_config(page_title="Claims Dashboard | FraudShield", page_icon="📋", layout="wide")
ui.inject_base_css()
st.title("📋 Claims Dashboard")
st.caption(
    "Every claim below has already been triaged by Claude. Filter the book, then drill into any "
    "claim to see the full evidence-based assessment and ask follow-up questions."
)

claims = data.load_claims()
cache = data.load_cache()

rows = []
for c in claims:
    a = cache.get(c["id"])
    rows.append(
        {
            "Claim ID": c["id"],
            "Claimant": c["claimant_name"],
            "Type": c["claim_type"],
            "Claimed Amount": c["claimed_amount"],
            "Risk Level": a["risk_level"] if a else "Not analyzed",
            "Risk Score": a["risk_score"] if a else None,
            "Recommended Action": a["recommended_action"] if a else "—",
            "Reported": c["reported_date"],
        }
    )
df = pd.DataFrame(rows)
analyzed = df[df["Risk Score"].notna()]
high_risk = analyzed[analyzed["Risk Level"] == "High"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total claims", len(df))
k2.metric("Total claimed", ui.fmt_currency(df["Claimed Amount"].sum()))
k3.metric("High-risk claims", len(high_risk))
k4.metric("$ flagged for investigation", ui.fmt_currency(high_risk["Claimed Amount"].sum()))

st.divider()

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    risk_counts = (
        analyzed["Risk Level"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0).reset_index()
    )
    risk_counts.columns = ["Risk Level", "Count"]
    status_colors = {"Low": "#0ca30c", "Medium": "#fab219", "High": "#d03b3b"}
    chart = (
        alt.Chart(risk_counts)
        .mark_bar(cornerRadiusEnd=4, size=28)
        .encode(
            x=alt.X("Count:Q", title="Claims"),
            y=alt.Y("Risk Level:N", sort=["High", "Medium", "Low"], title=None),
            color=alt.Color(
                "Risk Level:N",
                scale=alt.Scale(domain=list(status_colors.keys()), range=list(status_colors.values())),
                legend=None,
            ),
            tooltip=["Risk Level", "Count"],
        )
        .properties(height=160, title="Claims by risk level")
    )
    st.altair_chart(chart, width="stretch")

with chart_col2:
    type_amounts = df.groupby("Type", as_index=False)["Claimed Amount"].sum()
    chart2 = (
        alt.Chart(type_amounts)
        .mark_bar(cornerRadiusEnd=4, size=28)
        .encode(
            x=alt.X("Claimed Amount:Q", title="Total claimed ($)"),
            y=alt.Y("Type:N", sort="-x", title=None),
            color=alt.Color(
                "Type:N",
                scale=alt.Scale(domain=list(ui.CATEGORICAL.keys()), range=list(ui.CATEGORICAL.values())),
                legend=None,
            ),
            tooltip=["Type", "Claimed Amount"],
        )
        .properties(height=160, title="Claimed amount by type")
    )
    st.altair_chart(chart2, width="stretch")

st.divider()

fc1, fc2, fc3 = st.columns([1, 1, 2])
with fc1:
    risk_filter = st.multiselect(
        "Risk level", ["Low", "Medium", "High", "Not analyzed"],
        default=["Low", "Medium", "High", "Not analyzed"],
    )
with fc2:
    type_options = sorted(df["Type"].unique().tolist())
    type_filter = st.multiselect("Claim type", type_options, default=type_options)
with fc3:
    search = st.text_input("Search claimant or claim ID", "")

filtered = df[df["Risk Level"].isin(risk_filter) & df["Type"].isin(type_filter)]
if search:
    s = search.lower()
    filtered = filtered[
        filtered["Claim ID"].str.lower().str.contains(s) | filtered["Claimant"].str.lower().str.contains(s)
    ]

st.markdown(f"**{len(filtered)} of {len(df)} claims shown**")
display_df = filtered.copy()
display_df["Claimed Amount"] = display_df["Claimed Amount"].apply(ui.fmt_currency)
st.dataframe(display_df, width="stretch", hide_index=True)

st.divider()
st.subheader("🔍 Claim detail")

claim_ids = filtered["Claim ID"].tolist() or df["Claim ID"].tolist()
if not claim_ids:
    st.info("No claims match the current filters.")
else:
    selected_id = st.selectbox(
        "Select a claim to review",
        claim_ids,
        format_func=lambda cid: f"{cid} — {data.load_claim(cid)['claimant_name']}",
    )
    claim = data.load_claim(selected_id)
    assessment = cache.get(selected_id)

    detail_left, detail_right = st.columns([3, 2], gap="large")
    with detail_left:
        st.markdown(f"#### {claim['claimant_name']} · {claim['claim_type']} claim")
        st.caption(f"{claim['claim_number']} · Policy {claim['policy_number']} · Reported {claim['reported_date']}")
        st.write(claim["incident_description"])
        meta_cols = st.columns(3)
        meta_cols[0].metric("Claimed amount", ui.fmt_currency(claim["claimed_amount"]))
        meta_cols[1].metric("Prior claims (3y)", claim["prior_claims_last_3_years"])
        meta_cols[2].metric("Witnesses", claim["witnesses"])
        with st.expander("Full claim file"):
            st.json(claim)

    with detail_right:
        st.markdown("#### AI fraud assessment")
        if assessment:
            ui.render_assessment(assessment)
        else:
            st.info("This claim hasn't been analyzed yet.")

        if st.button("🔄 Run / re-run live AI analysis", key=f"analyze_{selected_id}", width="stretch"):
            with st.spinner("Claude is reviewing the claim file..."):
                try:
                    new_assessment = claude_client.analyze_claim(claim)
                    cache = data.update_cache_entry(selected_id, new_assessment)
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    if assessment:
        st.divider()
        st.markdown("#### 💬 Ask FraudShield about this claim")
        chat_key = f"chat_history_{selected_id}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []
        for turn in st.session_state[chat_key]:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])
        question = st.chat_input("e.g. Why wasn't the prior claims count a bigger factor?")
        if question:
            st.session_state[chat_key].append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        answer = claude_client.ask_about_claim(
                            claim, assessment, question, st.session_state[chat_key][:-1]
                        )
                    except RuntimeError as exc:
                        answer = f"⚠️ {exc}"
                st.write(answer)
            st.session_state[chat_key].append({"role": "assistant", "content": answer})
