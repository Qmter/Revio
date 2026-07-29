import asyncio
import logging
from sqlalchemy import select

from shared.core import async_session_maker
from shared.models import Review, PullRequest, ReviewComment
from shared.events import PRReviewCompletedEvent, ReviewCommentSchema
from .worker import process_notification

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_standalone_notification_test():
    """
    Тестовый запуск: берет из БД самый свежий завершенный Review (status='completed')
    и прогоняет его через Notification Service.
    """
    logger.info("🔍 Ищем завершенные ревью (status='completed') в PostgreSQL...")

    async with async_session_maker() as db:
        stmt = (
            select(Review, PullRequest)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .where(Review.status == "completed")
            .order_by(Review.completed_at.desc())
        )
        res = await db.execute(stmt)
        row = res.first()

        if not row:
            logger.info("💤 Нет завершенных ревью со статусом 'completed'.")
            return

        review, pr = row

        # Извлекаем замечания к строкам
        stmt_comments = select(ReviewComment).where(ReviewComment.review_id == review.id)
        comments_res = await db.execute(stmt_comments)
        db_comments = comments_res.scalars().all()

        comments_schema = [
            ReviewCommentSchema(
                file_path=c.file_path,
                line_number=c.line_number,
                severity=c.severity,
                comment_text=c.comment_text,
                suggested_code=c.suggested_code,
            )
            for c in db_comments
        ]

        # Генерируем событие завершения
        event = PRReviewCompletedEvent(
            review_id=review.id,
            pull_request_id=pr.id,
            github_repo_id=987654321,  # Наш тестовый repo ID
            github_pr_number=pr.github_pr_number,
            commit_sha=review.commit_sha,
            summary=review.summary or "Без резюме",
            score=review.score or 100,
            comments=comments_schema,
            tokens_used=review.tokens_used,
        )

        await process_notification(event)


if __name__ == "__main__":
    asyncio.run(run_standalone_notification_test())