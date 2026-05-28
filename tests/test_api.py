"""Tests for api.py — requests.get is mocked so no network calls are made."""
import json
import pytest
from unittest.mock import patch, MagicMock
from api import fetch_markets


def _mock_response(markets):
    """Build a mock requests.Response returning the given list."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = markets
    return mock


def _valid_market(**overrides):
    """Minimal valid market payload."""
    base = {
        "id": "market-1",
        "question": "Will X happen?",
        "active": True,
        "closed": False,
        "acceptingOrders": True,
        "volumeNum": 50000,
        "volume24hr": 5000,
        "outcomePrices": ["0.6", "0.4"],
        "slug": "will-x-happen",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------

def test_fetch_markets_returns_filtered_list():
    market = _valid_market()
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert len(result) == 1
    assert result[0]["market_id"] == "market-1"
    assert result[0]["market_name"] == "Will X happen?"
    assert result[0]["price"] == 0.6
    assert result[0]["volume"] == 50000
    assert result[0]["slug"] == "will-x-happen"


def test_fetch_markets_parses_outcome_prices_as_string():
    # outcomePrices sometimes comes as a JSON string instead of a list
    market = _valid_market(outcomePrices='["0.75", "0.25"]')
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result[0]["price"] == 0.75


def test_fetch_markets_defaults_price_to_0_5_when_no_outcome_prices():
    market = _valid_market(outcomePrices=[])
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result[0]["price"] == 0.5


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def test_fetch_markets_excludes_inactive():
    market = _valid_market(active=False)
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_excludes_closed():
    market = _valid_market(closed=True)
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_excludes_not_accepting_orders():
    market = _valid_market(acceptingOrders=False)
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_excludes_below_min_volume():
    market = _valid_market(volumeNum=100)  # below MIN_VOLUME default of 10000
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_excludes_below_min_volume_24hr():
    market = _valid_market(volume24hr=50)  # below MIN_VOLUME_24HR default of 1000
    with patch("api.requests.get", return_value=_mock_response([market])):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_filters_mix_of_valid_and_invalid():
    markets = [
        _valid_market(id="good", question="Good market"),
        _valid_market(id="bad", active=False),
    ]
    with patch("api.requests.get", return_value=_mock_response(markets)):
        result = fetch_markets()
    assert len(result) == 1
    assert result[0]["market_id"] == "good"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_fetch_markets_returns_empty_on_non_list_response():
    with patch("api.requests.get", return_value=_mock_response({"error": "bad"})):
        result = fetch_markets()
    assert result == []


def test_fetch_markets_returns_empty_on_request_exception():
    import requests
    with patch("api.requests.get", side_effect=requests.RequestException("timeout")):
        result = fetch_markets()
    assert result == []
