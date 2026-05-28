"""Tests for detector.py — DB calls are mocked so no database is needed."""
import pytest
from unittest.mock import patch
from detector import check_price_movement, check_volume_spike, check_strong_signal


def _rows(volume, count):
    """Return a list of dict-like rows all with the same volume."""
    return [{"volume": volume}] * count


# ---------------------------------------------------------------------------
# check_price_movement
# ---------------------------------------------------------------------------

def test_price_movement_no_prior_snapshot():
    with patch("detector.get_snapshot_5min_ago", return_value=None):
        triggered, change = check_price_movement("m1", 0.6)
    assert triggered is False
    assert change == 0.0


def test_price_movement_below_threshold():
    # 2% change — below the 4% threshold
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}):
        triggered, change = check_price_movement("m1", 0.52)
    assert triggered is False
    assert abs(change - 0.02) < 1e-9


def test_price_movement_exactly_at_threshold():
    # Exactly 4% — should trigger
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}):
        triggered, change = check_price_movement("m1", 0.54)
    assert triggered is True
    assert abs(change - 0.04) < 1e-9


def test_price_movement_upward():
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}):
        triggered, change = check_price_movement("m1", 0.57)
    assert triggered is True
    assert change > 0


def test_price_movement_downward():
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.6}):
        triggered, change = check_price_movement("m1", 0.54)
    assert triggered is True
    assert change < 0
    assert abs(change - (-0.06)) < 1e-9


def test_price_movement_returns_signed_change_even_when_not_triggered():
    # 1% drop — doesn't trigger, but signed change should still be correct
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}):
        triggered, change = check_price_movement("m1", 0.49)
    assert triggered is False
    assert abs(change - (-0.01)) < 1e-9


# ---------------------------------------------------------------------------
# check_volume_spike
# ---------------------------------------------------------------------------

def test_volume_spike_insufficient_history():
    with patch("detector.get_recent_snapshots", return_value=_rows(50000, 2)):
        result = check_volume_spike("m1", 200000)
    assert result is False


def test_volume_spike_not_triggered():
    # Average 50k, current 80k = 1.6x — below 2x multiplier
    with patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        result = check_volume_spike("m1", 80000)
    assert result is False


def test_volume_spike_exactly_at_multiplier():
    # Average 50k, current 100k = exactly 2x — should trigger
    with patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        result = check_volume_spike("m1", 100000)
    assert result is True


def test_volume_spike_triggered():
    with patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        result = check_volume_spike("m1", 120000)
    assert result is True


# ---------------------------------------------------------------------------
# check_strong_signal
# ---------------------------------------------------------------------------

def test_strong_signal_both_triggered():
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}), \
         patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        triggered, change = check_strong_signal("m1", 0.56, 110000)
    assert triggered is True
    assert change > 0


def test_strong_signal_price_only():
    # Price spikes but volume is low — not a strong signal
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}), \
         patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        triggered, change = check_strong_signal("m1", 0.56, 60000)
    assert triggered is False


def test_strong_signal_volume_only():
    # Volume spikes but no prior price snapshot — not a strong signal
    with patch("detector.get_snapshot_5min_ago", return_value=None), \
         patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        triggered, change = check_strong_signal("m1", 0.5, 110000)
    assert triggered is False
    assert change == 0.0


def test_strong_signal_neither():
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.5}), \
         patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        triggered, change = check_strong_signal("m1", 0.51, 60000)
    assert triggered is False


def test_strong_signal_propagates_price_change():
    # The returned price_change should be the signed delta, not abs
    with patch("detector.get_snapshot_5min_ago", return_value={"price": 0.65}), \
         patch("detector.get_recent_snapshots", return_value=_rows(50000, 5)):
        triggered, change = check_strong_signal("m1", 0.58, 110000)
    assert triggered is True
    assert change < 0  # price went down
