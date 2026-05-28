"""Tests for notifier.py — requests.post is mocked so no Telegram calls are made."""
import pytest
from unittest.mock import patch, MagicMock
from notifier import send_alert, send_message


def _mock_post():
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

def test_send_message_posts_to_telegram():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_message("Bot started. Monitoring 42 markets.")
    post.assert_called_once()
    payload = post.call_args.kwargs["json"]
    assert payload["text"] == "Bot started. Monitoring 42 markets."


def test_send_message_does_not_raise_on_failure():
    import requests
    with patch("notifier.requests.post", side_effect=requests.RequestException("fail")):
        send_message("test")  # must not raise


# ---------------------------------------------------------------------------
# send_alert — signal type routing
# ---------------------------------------------------------------------------

def test_send_alert_price_signal():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.6, 50000, "market-a", price_change=0.05)
    text = post.call_args.kwargs["json"]["text"]
    assert "📈" in text
    assert "PRICE MOVEMENT" in text


def test_send_alert_volume_signal():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "volume", 0.6, 50000, "market-a", price_change=0.01)
    text = post.call_args.kwargs["json"]["text"]
    assert "📊" in text
    assert "VOLUME SPIKE" in text


def test_send_alert_strong_signal():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "strong", 0.6, 50000, "market-a", price_change=0.07)
    text = post.call_args.kwargs["json"]["text"]
    assert "🚨" in text
    assert "STRONG SIGNAL" in text


def test_send_alert_unknown_type_does_not_post():
    with patch("notifier.requests.post") as post:
        send_alert("Market A", "m1", "unknown", 0.6, 50000, "market-a")
    post.assert_not_called()


# ---------------------------------------------------------------------------
# send_alert — message format (Feature 5)
# ---------------------------------------------------------------------------

def test_send_alert_price_formatted_as_percentage():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.642, 50000, "market-a", price_change=0.05)
    text = post.call_args.kwargs["json"]["text"]
    assert "64.2%" in text


def test_send_alert_move_up():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.6, 50000, "market-a", price_change=0.062)
    text = post.call_args.kwargs["json"]["text"]
    assert "UP +6.2%" in text


def test_send_alert_move_down():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.6, 50000, "market-a", price_change=-0.051)
    text = post.call_args.kwargs["json"]["text"]
    assert "DOWN -5.1%" in text


def test_send_alert_volume_formatted_with_commas():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.6, 1234567, "market-a", price_change=0.05)
    text = post.call_args.kwargs["json"]["text"]
    assert "$1,234,567" in text


def test_send_alert_includes_link():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "price", 0.6, 50000, "will-x-happen", price_change=0.05)
    text = post.call_args.kwargs["json"]["text"]
    assert "https://polymarket.com/market/will-x-happen" in text


def test_send_alert_includes_market_name():
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Will Trump win?", "m1", "price", 0.6, 50000, "slug", price_change=0.05)
    text = post.call_args.kwargs["json"]["text"]
    assert "Will Trump win?" in text


def test_send_alert_default_price_change_is_zero():
    # price_change defaults to 0.0 — should show UP +0.0% without crashing
    mock = _mock_post()
    with patch("notifier.requests.post", return_value=mock) as post:
        send_alert("Market A", "m1", "volume", 0.5, 50000, "slug")
    text = post.call_args.kwargs["json"]["text"]
    assert "UP +0.0%" in text


def test_send_alert_does_not_raise_on_request_failure():
    import requests
    with patch("notifier.requests.post", side_effect=requests.RequestException("fail")):
        send_alert("Market A", "m1", "price", 0.6, 50000, "slug", price_change=0.05)
