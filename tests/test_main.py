"""Tests for main.py — only is_on_cooldown is unit-tested here (the rest is I/O orchestration)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from main import is_on_cooldown


def _alert_row(minutes_ago):
    """Return a dict mimicking a db alerts row with sent_at set to N minutes ago (UTC)."""
    sent_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_ago)
    return {"sent_at": sent_at.isoformat(), "market_id": "m1", "signal_type": "price"}


# ---------------------------------------------------------------------------
# is_on_cooldown
# ---------------------------------------------------------------------------

def test_not_on_cooldown_when_no_prior_alert():
    with patch("main.get_last_alert", return_value=None):
        assert is_on_cooldown("m1", "price") is False


def test_on_cooldown_when_alert_sent_recently():
    # Alert sent 5 minutes ago — within the 15-minute cooldown
    with patch("main.get_last_alert", return_value=_alert_row(5)):
        assert is_on_cooldown("m1", "price") is True


def test_not_on_cooldown_when_alert_sent_long_ago():
    # Alert sent 20 minutes ago — outside the 15-minute cooldown
    with patch("main.get_last_alert", return_value=_alert_row(20)):
        assert is_on_cooldown("m1", "price") is False


def test_on_cooldown_at_boundary():
    # Exactly 14 minutes ago — still within the 15-minute window
    with patch("main.get_last_alert", return_value=_alert_row(14)):
        assert is_on_cooldown("m1", "price") is True


def test_not_on_cooldown_just_past_boundary():
    # Just over 15 minutes ago
    with patch("main.get_last_alert", return_value=_alert_row(16)):
        assert is_on_cooldown("m1", "price") is False


def test_is_on_cooldown_returns_false_on_exception():
    with patch("main.get_last_alert", side_effect=Exception("db error")):
        assert is_on_cooldown("m1", "price") is False
