from sqlalchemy import select, func
from .engine import async_session
from .models import Subscriber, Preferences

_VALID_PREF_FIELDS = {"signal_filter", "quiet_start", "quiet_end", "min_volume", "price_threshold"}

_DEFAULT_PREFS = {
    "signal_filter": "all",
    "quiet_start": None,
    "quiet_end": None,
    "min_volume": None,
    "price_threshold": None,
}


class SubscriberRepository:
    """ORM-backed access to subscribers and their per-account preferences."""

    async def add(self, chat_id: int, username: str = None):
        async with async_session() as session:
            if not await session.get(Subscriber, chat_id):
                session.add(Subscriber(chat_id=chat_id, username=username))
            if not await session.get(Preferences, chat_id):
                session.add(Preferences(chat_id=chat_id))
            await session.commit()

    async def remove(self, chat_id: int):
        async with async_session() as session:
            sub = await session.get(Subscriber, chat_id)
            if sub:
                await session.delete(sub)
                await session.commit()

    async def get_all_chat_ids(self) -> list[int]:
        async with async_session() as session:
            result = await session.execute(select(Subscriber.chat_id))
            return list(result.scalars().all())

    async def get_info(self, chat_id: int) -> Subscriber | None:
        async with async_session() as session:
            return await session.get(Subscriber, chat_id)

    async def count(self) -> int:
        async with async_session() as session:
            result = await session.execute(select(func.count()).select_from(Subscriber))
            return result.scalar_one()

    async def get_preferences(self, chat_id: int) -> Preferences | None:
        async with async_session() as session:
            return await session.get(Preferences, chat_id)

    async def upsert_preference(self, chat_id: int, field: str, value):
        if field not in _VALID_PREF_FIELDS:
            raise ValueError(f"Invalid preference field: {field}")
        async with async_session() as session:
            prefs = await session.get(Preferences, chat_id)
            if not prefs:
                prefs = Preferences(chat_id=chat_id)
                session.add(prefs)
            setattr(prefs, field, value)
            await session.commit()

    async def get_all_with_preferences(self) -> list[dict]:
        async with async_session() as session:
            stmt = (
                select(
                    Subscriber.chat_id,
                    func.coalesce(Preferences.signal_filter, "all").label("signal_filter"),
                    Preferences.quiet_start, Preferences.quiet_end,
                    Preferences.min_volume, Preferences.price_threshold,
                )
                .outerjoin(Preferences, Subscriber.chat_id == Preferences.chat_id)
            )
            result = await session.execute(stmt)
            return [dict(row._mapping) for row in result.all()]


subscriber_repo = SubscriberRepository()


async def add_subscriber(chat_id: int, username: str = None):
    await subscriber_repo.add(chat_id, username)


async def remove_subscriber(chat_id: int):
    await subscriber_repo.remove(chat_id)


async def get_all_subscribers() -> list[int]:
    return await subscriber_repo.get_all_chat_ids()


async def get_subscriber_info(chat_id: int) -> dict | None:
    sub = await subscriber_repo.get_info(chat_id)
    return sub.model_dump() if sub else None


async def count_subscribers() -> int:
    return await subscriber_repo.count()


async def get_preferences(chat_id: int) -> dict:
    prefs = await subscriber_repo.get_preferences(chat_id)
    return prefs.model_dump() if prefs else dict(_DEFAULT_PREFS)


async def upsert_preference(chat_id: int, field: str, value):
    await subscriber_repo.upsert_preference(chat_id, field, value)


async def get_all_subscriber_preferences() -> list[dict]:
    return await subscriber_repo.get_all_with_preferences()
