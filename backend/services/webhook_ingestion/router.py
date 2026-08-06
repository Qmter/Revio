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

# --- REST API ДЛЯ ФРОНТЕНДА ---
api_router = APIRouter(prefix="/api", tags=["Dashboard API"])


@api_router.get("/repositories")
async def get_repositories(db: AsyncSession = Depends(get_async_session)):
    """Список подключенных репозиториев"""
    stmt = select(Repository).order_by(Repository.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@api_router.get("/reviews")
async def get_reviews_history(db: AsyncSession = Depends(get_async_session)):
    """Лента всех проведенных AI-ревью"""
    stmt = (
        select(Review, PullRequest, Repository)
        .join(PullRequest, Review.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .order_by(Review.started_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    result = []
    for review, pr, repo in rows:
        result.append({
            "id": review.id,
            "repo_name": repo.full_name,
            "pr_number": pr.github_pr_number,
            "pr_title": pr.title,
            "author": pr.author_handle,
            "commit_sha": review.commit_sha[:7],
            "status": review.status,
            "score": review.score,
            "summary": review.summary,
            "started_at": review.started_at,
            "completed_at": review.completed_at,
        })
    return result


@api_router.get("/reviews/{review_id}")
async def get_review_details(review_id: str, db: AsyncSession = Depends(get_async_session)):
    """Детальная информация о конкретном ревью с точечными комментариями"""
    stmt = select(Review).where(Review.id == review_id)
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Для получения комментариев импортируем ReviewComment
    from shared.models import ReviewComment
    stmt_comments = select(ReviewComment).where(ReviewComment.review_id == review.id)
    comments_res = await db.execute(stmt_comments)
    comments = comments_res.scalars().all()

    return {
        "review": review,
        "comments": comments
    }

# --- ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ УПРАВЛЕНИЯ ---

@api_router.patch("/repositories/{repo_id}")
async def update_repository_rules(
    repo_id: str,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_async_session)
):
    """Обновление правил репозитория и статуса активности"""
    stmt = select(Repository).where(Repository.id == repo_id)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if "is_active" in payload:
        repo.is_active = payload["is_active"]
    if "custom_rules" in payload:
        repo.custom_rules = payload["custom_rules"]

    await db.commit()
    await db.refresh(repo)
    return repo


@api_router.post("/test-review")
async def trigger_test_review(
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_async_session)
):
    """Запуск тестового AI-ревью прямо из UI"""
    # Ищем первый активный репозиторий в БД
    stmt = select(Repository).where(Repository.is_active == True)
    res = await db.execute(stmt)
    repo = res.scalars().first()

    if not repo:
        raise HTTPException(status_code=400, detail="Нет активных репозиториев в БД")

    # Создаем тестовый PR
    import uuid
    from shared.models import PullRequest, Review
    from shared.events import PRReviewRequestedEvent

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=payload.get("pr_number", 42),
        title=payload.get("title", "Refactor authentication service and add async pool"),
        author_handle=payload.get("author", "yaroslav_dev"),
        head_sha="a1b2c3d4e5f678901234567890abcdef12345678",
        base_branch="main",
        state="open",
    )
    db.add(pr)
    await db.flush()

    review = Review(
        pull_request_id=pr.id,
        commit_sha=pr.head_sha,
        status="pending",
    )
    db.add(review)
    await db.commit()

    event = PRReviewRequestedEvent(
        review_id=review.id,
        repository_id=repo.id,
        github_repo_id=repo.github_repo_id,
        pull_request_id=pr.id,
        github_pr_number=pr.github_pr_number,
        commit_sha=pr.head_sha,
        author_handle=pr.author_handle,
        base_branch=pr.base_branch,
        custom_rules=repo.custom_rules or {},
    )

    await kafka_manager.send_event("pr-review-requests", event.model_dump())

    return {"status": "queued", "review_id": str(review.id)}