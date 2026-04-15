import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH, LOOKBACK_MINUTES, ALERT_COOLDOWN_MINUTES


def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database and create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            market_name TEXT NOT NULL,
            price REAL NOT NULL,
            volume REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    conn.close()


def insert_snapshot(market_id, market_name, price, volume):
    """Insert a market snapshot."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO snapshots (market_id, market_name, price, volume)
        VALUES (?, ?, ?, ?)
    """,
        (market_id, market_name, price, volume),
    )

    conn.commit()
    conn.close()


def get_snapshot_5min_ago(market_id):
    """Get snapshot from approximately 5 minutes ago."""
    conn = get_connection()
    cursor = conn.cursor()

    lookback_time = datetime.now() - timedelta(minutes=LOOKBACK_MINUTES)

    cursor.execute(
        """
        SELECT * FROM snapshots
        WHERE market_id = ? AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 1
    """,
        (market_id, lookback_time),
    )

    row = cursor.fetchone()
    conn.close()

    return row


def get_recent_snapshots(market_id, n=10):
    """Get last N snapshots for a market."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM snapshots
        WHERE market_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (market_id, n),
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_last_alert(market_id, signal_type):
    """Get the most recent alert for a market and signal type."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM alerts
        WHERE market_id = ? AND signal_type = ?
        ORDER BY sent_at DESC
        LIMIT 1
    """,
        (market_id, signal_type),
    )

    row = cursor.fetchone()
    conn.close()

    return row


def insert_alert(market_id, signal_type):
    """Insert an alert record."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO alerts (market_id, signal_type)
        VALUES (?, ?)
    """,
        (market_id, signal_type),
    )

    conn.commit()
    conn.close()
