import logging
from sqlalchemy import select

from shared.core import async_session_maker
from shared.models import Repository, User
from shared.events import PRReviewCompletedEvent
from .github_client import GitHubNotificationClient

logger = logging.getLogger(__name__)


def build_markdown_report(event: PRReviewCompletedEvent) -> str:
    """Генерирует аккуратную разметку Markdown для общего отчета в GitHub."""
    # Выбираем эмодзи в зависимости от оценки
    if event.score >= 80:
        badge = "🟢 **APPROVED**"
    elif event.score >= 50:
        badge = "🟡 **NEEDS IMPROVEMENT**"
    else:
        badge = "🔴 **CHANGES REQUESTED**"

    return f"""## 🤖 AI Code Review Summary

{badge} | **Quality Score:** `{event.score}/100`

### 📝 Общий вердикт:
{event.summary}

---
*Потрачено токенов LLM:* `{event.tokens_used}` | *Идентификатор прогона:* `{event.review_id}`
"""


async def process_notification(event: PRReviewCompletedEvent):
    """
    1. Находит токен владельца репозитория в БД.
    2. Формирует Markdown-отчет.
    3. Отправляет данные в GitHub API.
    """
    logger.info(f"📩 Отправка уведомления для PR #{event.github_pr_number}...")

    async with async_session_maker() as db:
        # Находим репозиторий и пользователя
        stmt = (
            select(Repository, User)
            .join(User, Repository.owner_id == User.id)
            .where(Repository.github_repo_id == event.github_repo_id)
        )
        res = await db.execute(stmt)
        row = res.first()

        if not row:
            logger.error(f"❌ Репозиторий {event.github_repo_id} не найден!")
            return

        repo, user = row

        # Подбираем тип вердикта для GitHub
        event_type = "COMMENT"
        if event.score < 50:
            event_type = "REQUEST_CHANGES"
        elif event.score >= 85:
            event_type = "APPROVE"

        # Преобразуем замечания в список словарей
        inline_comments = [c.model_dump() for c in event.comments]

        # Создаем клиент и публикуем
        client = GitHubNotificationClient(access_token=user.access_token)
        summary_md = build_markdown_report(event)

        await client.post_pull_request_review(
            full_name=repo.full_name,
            pull_number=event.github_pr_number,
            commit_sha=event.commit_sha,
            summary_markdown=summary_md,
            inline_comments=inline_comments,
            event_type=event_type,
        )