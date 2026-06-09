from datetime import datetime, timezone
from sqlalchemy import select, func, desc
from .engine import async_session
from .models import Alert, Snapshot


class AlertRepository:
    """ORM-backed access to alert history."""

    async def insert(self, market_id: str, signal_type: str):
        async with async_session() as session:
            session.add(Alert(market_id=market_id, signal_type=signal_type))
            await session.commit()

    async def get_last(self, market_id: str, signal_type: str) -> Alert | None:
        async with async_session() as session:
            result = await session.execute(
                select(Alert)
                .where(Alert.market_id == market_id, Alert.signal_type == signal_type)
                .order_by(desc(Alert.sent_at))
                .limit(1)
            )
            return result.scalars().first()

    async def get_recent(self, n: int = 5) -> list[dict]:
        async with async_session() as session:
            ranked = select(
                Snapshot.market_id, Snapshot.market_name,
                func.row_number().over(
                    partition_by=Snapshot.market_id, order_by=desc(Snapshot.timestamp)
                ).label("rn"),
            ).subquery()
            latest_names = select(ranked.c.market_id, ranked.c.market_name).where(ranked.c.rn == 1).subquery()

            stmt = (
                select(
                    Alert.market_id, Alert.signal_type, Alert.sent_at,
                    func.coalesce(latest_names.c.market_name, Alert.market_id).label("market_name"),
                )
                .outerjoin(latest_names, Alert.market_id == latest_names.c.market_id)
                .order_by(desc(Alert.sent_at))
                .limit(n)
            )
            result = await session.execute(stmt)
            return [dict(row._mapping) for row in result.all()]

    async def count_today(self) -> int:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).select_from(Alert).where(Alert.sent_at >= today_start)
            )
            return result.scalar_one()


alert_repo = AlertRepository()


def _as_dict(obj) -> dict | None:
    return obj.model_dump() if obj is not None else None


async def insert_alert(market_id: str, signal_type: str):
    await alert_repo.insert(market_id, signal_type)


async def get_last_alert(market_id: str, signal_type: str) -> dict | None:
    return _as_dict(await alert_repo.get_last(market_id, signal_type))


async def get_recent_alerts(n: int = 5) -> list[dict]:
    return await alert_repo.get_recent(n)


async def count_alerts_today() -> int:
    return await alert_repo.count_today()
