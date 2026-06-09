from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, desc, delete
from bot.config import LOOKBACK_MINUTES
from .engine import async_session
from .models import Snapshot


class SnapshotRepository:
    """ORM-backed access to market snapshots — portable across Postgres and SQLite
    via SQL window functions rather than backend-specific subqueries."""

    async def insert(self, market_id: str, market_name: str, price: float, volume: float, slug: str = None):
        async with async_session() as session:
            session.add(Snapshot(market_id=market_id, market_name=market_name, price=price, volume=volume, slug=slug))
            await session.commit()

    async def get_lookback(self, market_id: str) -> Snapshot | None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
        async with async_session() as session:
            result = await session.execute(
                select(Snapshot)
                .where(Snapshot.market_id == market_id, Snapshot.timestamp <= cutoff)
                .order_by(desc(Snapshot.timestamp))
                .limit(1)
            )
            return result.scalars().first()

    async def get_recent(self, market_id: str, n: int = 10) -> list[Snapshot]:
        async with async_session() as session:
            result = await session.execute(
                select(Snapshot)
                .where(Snapshot.market_id == market_id)
                .order_by(desc(Snapshot.timestamp))
                .limit(n)
            )
            return list(result.scalars().all())

    async def get_top_movers(self, n: int = 5) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
        async with async_session() as session:
            latest_ranked = select(
                Snapshot.market_id, Snapshot.market_name, Snapshot.price,
                Snapshot.volume, Snapshot.slug,
                func.row_number().over(
                    partition_by=Snapshot.market_id, order_by=desc(Snapshot.timestamp)
                ).label("rn"),
            ).subquery()
            latest = select(latest_ranked).where(latest_ranked.c.rn == 1).subquery()

            lookback_ranked = select(
                Snapshot.market_id, Snapshot.price.label("old_price"),
                func.row_number().over(
                    partition_by=Snapshot.market_id, order_by=desc(Snapshot.timestamp)
                ).label("rn"),
            ).where(Snapshot.timestamp <= cutoff).subquery()
            lookback = select(lookback_ranked).where(lookback_ranked.c.rn == 1).subquery()

            price_change = (latest.c.price - lookback.c.old_price)
            stmt = (
                select(
                    latest.c.market_id, latest.c.market_name, latest.c.price,
                    latest.c.volume, latest.c.slug, price_change.label("price_change"),
                )
                .join(lookback, latest.c.market_id == lookback.c.market_id)
                .order_by(desc(func.abs(price_change)))
                .limit(n)
            )
            result = await session.execute(stmt)
            return [dict(row._mapping) for row in result.all()]

    async def search(self, pattern: str) -> list[dict]:
        """`pattern` is a ready-to-use SQL LIKE pattern (e.g. '%election%')."""
        async with async_session() as session:
            ranked = select(
                Snapshot.market_id, Snapshot.market_name, Snapshot.price,
                Snapshot.volume, Snapshot.slug,
                func.row_number().over(
                    partition_by=Snapshot.market_id, order_by=desc(Snapshot.timestamp)
                ).label("rn"),
            ).where(func.lower(Snapshot.market_name).like(func.lower(pattern))).subquery()
            stmt = select(ranked).where(ranked.c.rn == 1).limit(5)
            result = await session.execute(stmt)
            return [dict(row._mapping) for row in result.all()]

    async def prune_old(self, days: int = 7) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with async_session() as session:
            result = await session.execute(delete(Snapshot).where(Snapshot.timestamp < cutoff))
            await session.commit()
            return result.rowcount


snapshot_repo = SnapshotRepository()


def _as_dict(obj) -> dict | None:
    return obj.model_dump() if obj is not None else None


async def insert_snapshot(market_id: str, market_name: str, price: float, volume: float, slug: str = None):
    await snapshot_repo.insert(market_id, market_name, price, volume, slug)


async def get_snapshot_lookback(market_id: str) -> dict | None:
    return _as_dict(await snapshot_repo.get_lookback(market_id))


async def get_recent_snapshots(market_id: str, n: int = 10) -> list[dict]:
    return [s.model_dump() for s in await snapshot_repo.get_recent(market_id, n)]


async def get_top_movers(n: int = 5) -> list[dict]:
    return await snapshot_repo.get_top_movers(n)


async def search_market_snapshot(pattern: str) -> list[dict]:
    return await snapshot_repo.search(pattern)


async def prune_old_snapshots(days: int = 7) -> int:
    return await snapshot_repo.prune_old(days)
