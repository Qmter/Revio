from datetime import datetime
import logging
from sqlalchemy import select

from shared.core import async_session_maker
from shared.models import Review, ReviewComment
from shared.events import PRReviewRequestedEvent, PRReviewCompletedEvent, ReviewCommentSchema
from .llm import llm_client

logger = logging.getLogger(__name__)


async def fetch_git_diff_mock(commit_sha: str) -> str:
    """
    Заглушка для получения Diff кода из GitHub API.
    В будущем здесь будет асинхронный вызов REST API GitHub:
    GET /repos/{owner}/{repo}/pulls/{pull_number}.diff
    """
    return f"""
diff --git a/services/webhook_ingestion/kafka.py b/services/webhook_ingestion/kafka.py
index 1234567..89abcde 100644
--- a/services/webhook_ingestion/kafka.py
+++ b/services/webhook_ingestion/kafka.py
@@ -15,6 +15,7 @@ class KafkaProducerManager:
         try:
             await producer.start()
         except Exception as e:
+            # TODO: Fix unclosed producer warning
             logger.warning(f"Failed to connect:" + str(e))

diff --git a/services/webhook_ingestion/router.py b/services/webhook_ingestion/router.py
index 9876543..fedcba9 100644
--- a/services/webhook_ingestion/router.py
+++ b/services/webhook_ingestion/router.py
@@ -40,4 +40,5 @@ async def handle_github_webhook(...):
     db.add(review)
     await db.commit()
+    # Missing error handling if DB fails
     return {{"status": "queued"}}
"""


async def process_review_request(event: PRReviewRequestedEvent) -> PRReviewCompletedEvent:
    """
    Главная бизнес-логика воркера:
    1. Ищет Review по его точечному review_id и переводит в статус 'processing'.
    2. Извлекает Git Diff.
    3. Отправляет запрос в Gemini / Ollama.
    4. Записывает результат и замечания по строкам в БД.
    5. Переводит Review в статус 'completed'.
    """
    logger.info(f"🚀 Начинаем AI-ревью для PR #{event.github_pr_number} (Commit: {event.commit_sha[:7]})")

    async with async_session_maker() as db:
        # 1. Находим точный Review по его первичным ключам (UUID review_id)
        stmt = select(Review).where(Review.id == event.review_id)  # <--- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
        res = await db.execute(stmt)
        review = res.scalar_one_or_none()

        if not review:
            logger.error(f"❌ Review {event.review_id} не найден в БД")
            raise ValueError("Review not found in database")

        review.status = "processing"
        await db.commit()

        # 2. Получаем Diff изменений
        git_diff = await fetch_git_diff_mock(event.commit_sha)

        # 3. Отправляем в Gemini / Ollama
        ai_response = await llm_client.analyze_code(
            git_diff=git_diff,
            custom_rules=event.custom_rules,
        )

        # 4. Сохраняем итоговые данные ревью
        review.summary = ai_response.get("summary")
        review.score = ai_response.get("score")
        review.tokens_used = ai_response.get("tokens_used", 0)
        review.status = "completed"
        review.completed_at = datetime.utcnow()

        # 5. Сохраняем замечания к конкретным строкам
        comments_list = []
        for raw_comment in ai_response.get("comments", []):
            db_comment = ReviewComment(
                review_id=review.id,
                file_path=raw_comment["file_path"],
                line_number=raw_comment["line_number"],
                severity=raw_comment.get("severity", "info"),
                comment_text=raw_comment["comment_text"],
                suggested_code=raw_comment.get("suggested_code"),
            )
            db.add(db_comment)

            comments_list.append(
                ReviewCommentSchema(
                    file_path=raw_comment["file_path"],
                    line_number=raw_comment["line_number"],
                    severity=raw_comment.get("severity", "info"),
                    comment_text=raw_comment["comment_text"],
                    suggested_code=raw_comment.get("suggested_code"),
                )
            )

        await db.commit()
        logger.info(f"✅ AI-ревью успешно завершено! Оценка: {review.score}/100. Замечаний: {len(comments_list)}")

        return PRReviewCompletedEvent(
            review_id=review.id,
            pull_request_id=event.pull_request_id,
            github_repo_id=event.github_repo_id,
            github_pr_number=event.github_pr_number,
            commit_sha=event.commit_sha,
            summary=review.summary,
            score=review.score,
            comments=comments_list,
            tokens_used=review.tokens_used,
        )