from sqlalchemy. ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from sqlalchemy.orm import DeclarativeBase
from .config import settings


async_engine = create_async_engine(
    url=settings.DB_ASYNC_URL,
    echo=True
)

# Фабрика асинхронных сессий (привязанная к движку)
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Базовый класс для всех моделей SQLAlchemy
class Base(DeclarativeBase):
    pass

# Dependency для получения сессии БД в FastAPI
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session