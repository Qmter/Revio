import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, Header, Depends, HTTPException, status, Body  # <--- Добавили Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.core import get_async_session
from shared.models import Repository, PullRequest, Review
from shared.events import PRReviewRequestedEvent
from .security import verify_github_signature
from .kafka import kafka_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Пример JSON вебхука GitHub для отображения в Swagger UI
GITHUB_WEBHOOK_EXAMPLE = {
    "action": "opened",
    "repository": {
        "id": 987654321,
        "full_name": "octocat/Hello-World"
    },
    "pull_request": {
        "number": 1,
        "title": "Fix memory leak in background worker",
        "user": {
            "login": "yaroslav_dev"
        },
        "head": {
            "sha": "a1b2c3d4e5f678901234567890abcdef12345678"
        },
        "base": {
            "ref": "main"
        }
    }
}


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    # Добавляем Body, чтобы Swagger нарисовал поле с JSON и автозаполнением:
    payload: Dict[str, Any] = Body(..., example=GITHUB_WEBHOOK_EXAMPLE),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_async_session),
):
    # 1. Мы обрабатываем только события типа 'pull_request'
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"Event '{x_github_event}' is not handled"}

    # Читаем сырое тело запроса для проверки подписи
    body_bytes = await request.body()

    action = payload.get("action")
    # Интересуют только открытие PR или добавление новых коммитов
    if action not in ["opened", "synchronize"]:
        return {"status": "ignored", "reason": f"Action '{action}' does not trigger AI review"}

    github_repo_id = payload.get("repository", {}).get("id")

    # 2. Ищем репозиторий в нашей БД
    stmt = select(Repository).where(Repository.github_repo_id == github_repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo or not repo.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not registered or inactive in AI Reviewer",
        )

    # 3. Проверяем подлинность вебхука через HMAC (если у репозитория задан webhook_secret)
    if repo.webhook_secret:
        verify_github_signature(body_bytes, repo.webhook_secret, x_hub_signature_256)

    # 4. Извлекаем данные о Pull Request
    pr_data = payload["pull_request"]
    github_pr_number = pr_data["number"]
    head_sha = pr_data["head"]["sha"]

    # Ищем, существует ли уже этот PR в нашей БД
    stmt_pr = select(PullRequest).where(
        PullRequest.repository_id == repo.id,
        PullRequest.github_pr_number == github_pr_number,
    )
    res_pr = await db.execute(stmt_pr)
    pr = res_pr.scalar_one_or_none()

    if not pr:
        # Создаем новую запись PR
        pr = PullRequest(
            repository_id=repo.id,
            github_pr_number=github_pr_number,
            title=pr_data["title"],
            author_handle=pr_data["user"]["login"],
            head_sha=head_sha,
            base_branch=pr_data["base"]["ref"],
            state="open",
        )
        db.add(pr)
        await db.flush()  # Чтобы получить сгенерированный pr.id
    else:
        # Обновляем коммит и заголовок
        pr.head_sha = head_sha
        pr.title = pr_data["title"]

    # 5. Создаем новый прогон AI-ревью со статусом 'pending'
    review = Review(
        pull_request_id=pr.id,
        commit_sha=head_sha,
        status="pending",
    )
    db.add(review)
    await db.commit()

    # 6. Формируем событие Kafka через нашу Pydantic-схему
    event = PRReviewRequestedEvent(
        review_id=review.id,
        repository_id=repo.id,
        github_repo_id=repo.github_repo_id,
        pull_request_id=pr.id,
        github_pr_number=pr.github_pr_number,
        commit_sha=head_sha,
        author_handle=pr.author_handle,
        base_branch=pr.base_branch,
        custom_rules=repo.custom_rules or {},
    )

    # 7. Отправляем событие в топик 'pr-review-requests'
    await kafka_manager.send_event("pr-review-requests", event.model_dump())

    return {
        "status": "queued",
        "review_id": str(review.id),
        "message": "AI Review task successfully pushed to queue",
    }