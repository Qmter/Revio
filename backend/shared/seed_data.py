import asyncio
from shared.core import async_session_maker
from shared.models import User, Repository


async def seed():
    async with async_session_maker() as session:
        # 1. Создаем тестового пользователя
        user = User(
            github_id=123456,
            username="yaroslav_dev",
            email="test@example.com",
            access_token="gho_fake_token_12345",
        )
        session.add(user)
        await session.flush()  # Чтобы получить user.id

        # 2. Создаем тестовый репозиторий
        repo = Repository(
            github_repo_id=987654321,  # ID репозитория в GitHub
            owner_id=user.id,
            full_name="octocat/Hello-World",
            is_active=True,
            custom_rules={"enforce_pep8": True, "max_line_length": 120},
            webhook_secret=None,  # Пока без HMAC проверки для простоты теста
        )
        session.add(repo)
        await session.commit()
        print("✅ Тестовый пользователь и репозиторий 'octocat/Hello-World' добавлены!")


if __name__ == "__main__":
    asyncio.run(seed())