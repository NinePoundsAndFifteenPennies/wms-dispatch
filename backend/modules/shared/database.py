from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from modules.shared.config import settings


def to_async_database_url(database_url: str) -> str:
    if database_url.startswith('postgresql+asyncpg://'):
        return database_url
    if database_url.startswith('postgresql://'):
        return database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    scheme = database_url.split('://', 1)[0] if '://' in database_url else 'unknown'
    raise RuntimeError(f'Only PostgreSQL database URLs are supported, got: {scheme}')


engine = create_async_engine(to_async_database_url(settings.database_url))
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
