import asyncio
import logging
from sqlalchemy import select

from shared.core import async_session_maker
from shared.models import Review, PullRequest, Repository
from shared.events import PRReviewRequestedEvent
from .worker import process_review_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_standalone_test():
    """
    Локальный запуск: ищет последнюю задачу со статусом 'pending' в БД
    и прогоняет её через AI Engine.
    """
    logger.info("🔍 Ищем задачи со статусом 'pending' в PostgreSQL...")

    async with async_session_maker() as db:
        stmt = (
            select(Review, PullRequest, Repository)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(Review.status == "pending")
            .order_by(Review.started_at.desc())
        )
        res = await db.execute(stmt)
        row = res.first()

        if not row:
            logger.info("💤 Нет задач со статусом 'pending' для обработки.")
            return

        review, pr, repo = row

        event = PRReviewRequestedEvent(
            review_id=review.id,  # <--- ПЕРЕДАЕМ ТОЧНЫЙ review_id
            repository_id=repo.id,
            github_repo_id=repo.github_repo_id,
            pull_request_id=pr.id,
            github_pr_number=pr.github_pr_number,
            commit_sha=review.commit_sha,
            author_handle=pr.author_handle,
            base_branch=pr.base_branch,
            custom_rules=repo.custom_rules or {},
        )

        completed_event = await process_review_request(event)
        
        print("\n" + "="*50)
        print(f"📊 ВЕРДИКТ AI (Оценка: {completed_event.score}/100):")
        print(f"📝 Резюме: {completed_event.summary}")
        print(f"💬 Замечаний найдено: {len(completed_event.comments)}")
        for c in completed_event.comments:
            print(f"  • [{c.severity.upper()}] {c.file_path}:{c.line_number} -> {c.comment_text}")
        print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_standalone_test())