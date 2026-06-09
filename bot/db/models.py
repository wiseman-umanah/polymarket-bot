from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, SmallInteger
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# SQLite only treats a column as an alias for its ROWID (and thus autoincrements
# it) when its declared type is exactly INTEGER PRIMARY KEY — BIGINT breaks that.
# `with_variant` keeps BIGINT/BIGSERIAL on Postgres while using INTEGER on SQLite.
_AutoBigInt = BigInteger().with_variant(Integer, "sqlite")


class Snapshot(SQLModel, table=True):
    __tablename__ = "snapshots"
    __table_args__ = (
        # hot path: get_lookback + get_recent filter on market_id then sort by timestamp
        Index("idx_snapshots_market_ts", "market_id", "timestamp"),
        # prune_old_snapshots deletes by timestamp alone — needs its own index
        Index("idx_snapshots_ts", "timestamp"),
    )

    id: int | None = Field(default=None, sa_column=Column(_AutoBigInt, primary_key=True, autoincrement=True))
    market_id: str
    market_name: str
    price: float
    volume: float
    slug: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True)))


class Alert(SQLModel, table=True):
    __tablename__ = "alerts"
    __table_args__ = (
        # get_last_alert runs on every market every poll cycle — must be fast
        Index("idx_alerts_market_signal_time", "market_id", "signal_type", "sent_at"),
    )

    id: int | None = Field(default=None, sa_column=Column(_AutoBigInt, primary_key=True, autoincrement=True))
    market_id: str
    signal_type: str
    sent_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True)))


class Subscriber(SQLModel, table=True):
    __tablename__ = "subscribers"

    chat_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    username: str | None = None
    joined_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True)))


class Preferences(SQLModel, table=True):
    __tablename__ = "preferences"

    chat_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    signal_filter: str = Field(default="all")
    quiet_start: int | None = Field(default=None, sa_column=Column(SmallInteger))
    quiet_end: int | None = Field(default=None, sa_column=Column(SmallInteger))
    min_volume: float | None = None
    price_threshold: float | None = None
