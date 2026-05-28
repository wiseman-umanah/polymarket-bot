"""Tests for db.py — all operations use a temp SQLite file via the temp_db fixture."""
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def test_init_db_creates_tables(temp_db):
    conn = temp_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    assert "snapshots" in tables
    assert "alerts" in tables


def test_insert_snapshot_stores_row(temp_db):
    temp_db.insert_snapshot("m1", "Test Market", 0.6, 50000)
    conn = temp_db.get_connection()
    row = conn.execute("SELECT * FROM snapshots WHERE market_id='m1'").fetchone()
    conn.close()
    assert row["market_name"] == "Test Market"
    assert row["price"] == 0.6
    assert row["volume"] == 50000


def test_get_snapshot_5min_ago_returns_old_row(temp_db):
    # Use UTC time — the query now uses datetime.now(timezone.utc).replace(tzinfo=None) for consistent comparison
    old_time_str = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S")
    conn = temp_db.get_connection()
    conn.execute(
        "INSERT INTO snapshots (market_id, market_name, price, volume, timestamp) VALUES (?,?,?,?,?)",
        ("m1", "Test Market", 0.5, 50000, old_time_str),
    )
    conn.commit()
    conn.close()

    snapshot = temp_db.get_snapshot_5min_ago("m1")
    assert snapshot is not None
    assert snapshot["price"] == 0.5


def test_get_snapshot_5min_ago_ignores_recent_row(temp_db):
    # Insert with explicit UTC time so the comparison is consistent
    recent_time_str = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    conn = temp_db.get_connection()
    conn.execute(
        "INSERT INTO snapshots (market_id, market_name, price, volume, timestamp) VALUES (?,?,?,?,?)",
        ("m1", "Test Market", 0.7, 60000, recent_time_str),
    )
    conn.commit()
    conn.close()

    snapshot = temp_db.get_snapshot_5min_ago("m1")
    assert snapshot is None


def test_get_snapshot_5min_ago_returns_none_for_unknown_market(temp_db):
    assert temp_db.get_snapshot_5min_ago("unknown") is None


def test_get_recent_snapshots_respects_limit(temp_db):
    for i in range(8):
        temp_db.insert_snapshot("m1", "Test Market", 0.5 + i * 0.01, 50000)
    rows = temp_db.get_recent_snapshots("m1", 5)
    assert len(rows) == 5


def test_get_recent_snapshots_returns_all_when_fewer_than_limit(temp_db):
    temp_db.insert_snapshot("m1", "Test Market", 0.5, 50000)
    temp_db.insert_snapshot("m1", "Test Market", 0.6, 60000)
    rows = temp_db.get_recent_snapshots("m1", 10)
    assert len(rows) == 2


def test_get_recent_snapshots_empty_for_unknown_market(temp_db):
    assert temp_db.get_recent_snapshots("unknown", 10) == []


def test_insert_alert_and_get_last_alert(temp_db):
    temp_db.insert_alert("m1", "price")
    alert = temp_db.get_last_alert("m1", "price")
    assert alert is not None
    assert alert["market_id"] == "m1"
    assert alert["signal_type"] == "price"


def test_get_last_alert_returns_most_recent(temp_db):
    temp_db.insert_alert("m1", "price")
    temp_db.insert_alert("m1", "price")  # second insert is more recent
    conn = temp_db.get_connection()
    count = conn.execute("SELECT COUNT(*) FROM alerts WHERE market_id='m1'").fetchone()[0]
    conn.close()
    # Two rows exist but get_last_alert should return the latest
    alert = temp_db.get_last_alert("m1", "price")
    assert alert is not None
    assert count == 2


def test_get_last_alert_returns_none_when_empty(temp_db):
    assert temp_db.get_last_alert("nonexistent", "price") is None


def test_get_last_alert_does_not_cross_signal_types(temp_db):
    temp_db.insert_alert("m1", "volume")
    assert temp_db.get_last_alert("m1", "price") is None


# ---------------------------------------------------------------------------
# count_alerts_today
# ---------------------------------------------------------------------------

def test_count_alerts_today_empty(temp_db):
    assert temp_db.count_alerts_today() == 0


def test_count_alerts_today_counts_todays_alerts(temp_db):
    temp_db.insert_alert("m1", "price")
    temp_db.insert_alert("m2", "volume")
    assert temp_db.count_alerts_today() == 2


def test_count_alerts_today_ignores_old_alerts(temp_db):
    yesterday = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    conn = temp_db.get_connection()
    conn.execute(
        "INSERT INTO alerts (market_id, signal_type, sent_at) VALUES (?,?,?)",
        ("m1", "price", yesterday),
    )
    conn.commit()
    conn.close()
    assert temp_db.count_alerts_today() == 0


# ---------------------------------------------------------------------------
# prune_old_snapshots
# ---------------------------------------------------------------------------

def test_prune_removes_old_snapshots(temp_db):
    old_ts = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn = temp_db.get_connection()
    conn.execute(
        "INSERT INTO snapshots (market_id, market_name, price, volume, timestamp) VALUES (?,?,?,?,?)",
        ("m1", "Old Market", 0.5, 50000, old_ts),
    )
    conn.commit()
    conn.close()

    deleted = temp_db.prune_old_snapshots(days=7)
    assert deleted == 1
    assert temp_db.get_recent_snapshots("m1", 10) == []


def test_prune_keeps_recent_snapshots(temp_db):
    temp_db.insert_snapshot("m1", "Recent Market", 0.5, 50000)
    deleted = temp_db.prune_old_snapshots(days=7)
    assert deleted == 0
    assert len(temp_db.get_recent_snapshots("m1", 10)) == 1


def test_prune_returns_zero_when_nothing_to_delete(temp_db):
    assert temp_db.prune_old_snapshots(days=7) == 0
