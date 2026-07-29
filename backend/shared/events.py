from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from uuid6 import uuid7


class SeverityEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ReviewCommentSchema(BaseModel):
    """Схема отдельного замечания AI к конкретной строке файла."""
    file_path: str = Field(..., description="Путь к файлу, например src/main.py")
    line_number: int = Field(..., description="Номер строки в файле")
    severity: SeverityEnum = Field(..., description="Уровень критичности (info/warning/critical)")
    comment_text: str = Field(..., description="Текст замечания от AI")
    suggested_code: Optional[str] = Field(None, description="Предложенный исправленный фрагмент кода")


class PRReviewRequestedEvent(BaseModel):
    """
    Топик Kafka: 'pr-review-requests'
    Отправляет: Webhook Ingestion Service
    Принимает: AI Review Engine
    """
    event_id: UUID = Field(default_factory=uuid7, description="Уникальный ID события (UUIDv7)")
    review_id: UUID = Field(..., description="ID записи в таблице reviews")  # <--- ДОБАВИЛИ ЭТУ СТРОКУ
    repository_id: UUID = Field(..., description="ID репозитория в нашей БД")
    github_repo_id: int = Field(..., description="ID репозитория в GitHub")
    pull_request_id: UUID = Field(..., description="ID PR в нашей БД")
    github_pr_number: int = Field(..., description="Номер PR в GitHub (#42)")
    commit_sha: str = Field(..., description="Хэш проверяемого коммита")
    author_handle: str = Field(..., description="Логин автора PR")
    base_branch: str = Field(..., description="Целевая ветка (main/master)")
    custom_rules: Dict[str, Any] = Field(default_factory=dict, description="Кастомные правила для AI")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PRReviewCompletedEvent(BaseModel):
    """
    Топик Kafka: 'pr-review-completed'
    Отправляет: AI Review Engine
    Принимает: Notification Service
    """
    event_id: UUID = Field(default_factory=uuid7)
    review_id: UUID = Field(..., description="ID прогона из таблицы reviews")
    pull_request_id: UUID
    github_repo_id: int
    github_pr_number: int
    commit_sha: str
    summary: str = Field(..., description="Общее резюме от AI по всему PR")
    score: int = Field(..., ge=1, le=100, description="Оценка качества кода (1-100)")
    comments: List[ReviewCommentSchema] = Field(default_factory=list)
    tokens_used: int = Field(default=0, description="Потрачено токенов LLM")
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class PRReviewFailedEvent(BaseModel):
    """
    Топик Kafka: 'pr-review-failed'
    Отправляет: AI Review Engine
    Принимает: Notification Service
    """
    event_id: UUID = Field(default_factory=uuid7)
    review_id: UUID
    pull_request_id: UUID
    github_repo_id: int
    github_pr_number: int
    commit_sha: str
    error_code: str = Field(..., description="Код ошибки (например, LLM_TIMEOUT)")
    error_message: str = Field(..., description="Описание ошибки")
    failed_at: datetime = Field(default_factory=datetime.utcnow)