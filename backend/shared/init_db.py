import asyncio
from .core import async_engine, Base
# Обязательно импортируем модели, чтобы SQLAlchemy «узнала» о таблицах
from .models import User, Repository, PullRequest, Review, ReviewComment  


async def init_tables():
    print("🚀 Подключаемся к PostgreSQL и создаем таблицы...")
    async with async_engine.begin() as conn:
        # Если захочешь сбросить базу и пересоздать с нуля — раскомментируй строку ниже:
        # await conn.run_sync(Base.metadata.drop_all)
        
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Все таблицы (users, repositories, pull_requests, reviews, review_comments) успешно созданы!")


if __name__ == "__main__":
    asyncio.run(init_tables())