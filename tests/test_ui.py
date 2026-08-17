from fraudshield import ui


def test_fmt_currency_rounds_to_whole_dollars():
    assert ui.fmt_currency(1234.5) == "$1,234"


def test_fmt_currency_adds_thousands_separators():
    assert ui.fmt_currency(1000000) == "$1,000,000"


def test_fmt_currency_non_numeric_falls_back_to_str():
    assert ui.fmt_currency("n/a") == "n/a"


def test_risk_badge_contains_level_and_matching_status_color():
    html = ui.risk_badge_html("High")
    assert "High risk" in html
    assert ui.STATUS["High"]["text"] in html


def test_action_badge_maps_escalate_to_high_status():
    html = ui.action_badge_html("Escalate to SIU")
    assert "Escalate to SIU" in html
    assert ui.STATUS["High"]["text"] in html


def test_action_badge_maps_approve_to_low_status():
    html = ui.action_badge_html("Approve")
    assert ui.STATUS["Low"]["text"] in html


def test_action_badge_unknown_action_defaults_to_medium():
    html = ui.action_badge_html("Some Unexpected Action")
    assert ui.STATUS["Medium"]["text"] in html


def test_red_flag_html_includes_severity_class_for_styling_hook():
    html = ui.red_flag_html({"flag": "Early inception", "severity": "High", "explanation": "why"})
    assert "fs-flag-High" in html
    assert "Early inception" in html
    assert "why" in html
