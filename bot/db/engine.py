from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from bot.config import DATABASE_URL, SQLITE_PATH


def _async_url() -> str:
    """Build an async SQLAlchemy URL from config — Postgres via asyncpg, SQLite via aiosqlite."""
    if DATABASE_URL:
        url = DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url
    return f"sqlite+aiosqlite:///{SQLITE_PATH}"


is_postgres = bool(DATABASE_URL)

engine = create_async_engine(_async_url())

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
