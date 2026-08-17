"""Shared color tokens and small rendering helpers for the Streamlit UI.

Color roles follow a status/categorical split: Low/Medium/High risk always use
the reserved status palette (never reused for anything else), and claim-type
charts use a small fixed-order categorical palette. Both are validated for
colorblind-safe contrast.
"""
import streamlit as st

# Status palette (reserved for risk level / recommended action, never used for series identity)
STATUS = {
    "Low": {"bg": "#e6f6e6", "text": "#0a7a0a", "icon": "●"},
    "Medium": {"bg": "#fef3d6", "text": "#8a5a00", "icon": "▲"},
    "High": {"bg": "#fbe7e7", "text": "#a52222", "icon": "✕"},
}

# Fixed-order categorical palette, used only for claim-type identity in charts
CATEGORICAL = {
    "Auto": "#2a78d6",
    "Property": "#eb6834",
    "Health": "#1baf7a",
    "Liability": "#eda100",
}

ACTION_STATUS = {
    "Approve": "Low",
    "Request More Information": "Medium",
    "Investigate": "Medium",
    "Escalate to SIU": "High",
}


def _pill_html(label: str, status_key: str) -> str:
    s = STATUS.get(status_key, STATUS["Medium"])
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{s["bg"]};color:{s["text"]};padding:3px 12px;border-radius:999px;'
        f'font-weight:600;font-size:0.85rem;white-space:nowrap;">'
        f'{s["icon"]} {label}</span>'
    )


def risk_badge_html(risk_level: str) -> str:
    return _pill_html(f"{risk_level} risk", risk_level)


def action_badge_html(action: str) -> str:
    return _pill_html(action, ACTION_STATUS.get(action, "Medium"))


def fmt_currency(amount) -> str:
    try:
        return f"${amount:,.0f}"
    except (TypeError, ValueError):
        return str(amount)


def inject_base_css():
    st.markdown(
        """
        <style>
        .fs-hero {
            background: linear-gradient(135deg, #0d3b73, #1c5cab);
            color: white;
            border-radius: 16px;
            padding: 2.25rem 2.5rem;
            margin-bottom: 1.5rem;
        }
        .fs-hero h1 { color: white; margin-bottom: 0.25rem; }
        .fs-hero p { color: #dce8f7; font-size: 1.05rem; margin-bottom: 0; }
        .fs-card {
            border: 1px solid rgba(11,11,11,0.08);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            background: #fcfcfb;
            margin-bottom: 0.75rem;
        }
        .fs-flag {
            border-left: 4px solid #c3c2b7;
            padding: 0.55rem 0.9rem;
            margin-bottom: 0.5rem;
            background: #fbfbfa;
            border-radius: 6px;
        }
        .fs-flag-High { border-left-color: #d03b3b; }
        .fs-flag-Medium { border-left-color: #fab219; }
        .fs-flag-Low { border-left-color: #0ca30c; }
        .fs-muted { color: #6b6a66; font-size: 0.85rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_assessment(assessment: dict):
    """Render a full fraud assessment result (score, summary, action, red flags)."""
    st.markdown(
        risk_badge_html(assessment["risk_level"]) + "&nbsp;&nbsp;" + f"**Score: {assessment['risk_score']}/100**",
        unsafe_allow_html=True,
    )
    st.progress(min(max(assessment["risk_score"], 0), 100) / 100)
    st.write(assessment["summary"])
    st.markdown(
        "**Recommended action:** " + action_badge_html(assessment["recommended_action"]),
        unsafe_allow_html=True,
    )
    st.caption(f"Model confidence: {assessment.get('confidence', 0):.0%}")
    if assessment.get("red_flags"):
        st.markdown("**Red flags**")
        for flag in assessment["red_flags"]:
            st.markdown(red_flag_html(flag), unsafe_allow_html=True)
    else:
        st.success("No red flags identified.")


def red_flag_html(flag: dict) -> str:
    severity = flag.get("severity", "Medium")
    return (
        f'<div class="fs-flag fs-flag-{severity}">'
        f'<strong>{flag.get("flag", "")}</strong> '
        f'<span class="fs-muted">({severity} severity)</span>'
        f'<div>{flag.get("explanation", "")}</div>'
        f"</div>"
    )
