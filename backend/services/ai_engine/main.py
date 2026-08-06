import asyncio
import logging
from sqlalchemy import select

from shared.core import async_session_maker
from shared.models import Review, PullRequest, Repository
from shared.events import PRReviewRequestedEvent
from .worker import process_review_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

async def run_worker():
    """
    Бесконечный фоновый воркер: каждые 3 секунды ищет задачи со статусом 'pending'
    и отправляет их на обработку в AI Engine.
    """
    logger.info("🚀 AI Engine запущен и готов обрабатывать задачи...")

    while True:
        try:
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

                if row:
                    review, pr, repo = row
                    logger.info(f"⚡ Найдена задача для PR #{pr.github_pr_number} (Review ID: {review.id})")

                    event = PRReviewRequestedEvent(
                        review_id=review.id,
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

                    print("\n" + "=" * 50)
                    print(f"📊 ВЕРДИКТ AI (Оценка: {completed_event.score}/100):")
                    print(f"📝 Резюме: {completed_event.summary}")
                    print(f"💬 Замечаний найдено: {len(completed_event.comments)}")
                    for c in completed_event.comments:
                        print(f"  • [{c.severity.upper()}] {c.file_path}:{c.line_number} -> {c.comment_text}")
                    print("=" * 50 + "\n")

        except Exception as e:
            logger.error(f"❌ Ошибка в работе AI Engine воркера: {e}")

        # Пауза перед следующей проверкой
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(run_worker())