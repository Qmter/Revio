import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class GitHubNotificationClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.base_url = "https://api.github.com"

    async def post_pull_request_review(
        self,
        full_name: str,          # "octocat/Hello-World"
        pull_number: int,        # 1
        commit_sha: str,         # "a1b2c3d..."
        summary_markdown: str,   # Общий текст отчёта
        inline_comments: List[Dict[str, Any]],
        event_type: str = "COMMENT",  # "APPROVE", "COMMENT", "REQUEST_CHANGES"
    ) -> bool:
        """
        Публикует полноценный PR Review с точечными комментариями.
        """
        if not self.access_token or self.access_token.startswith("gho_fake"):
            logger.warning("⚠️ GitHub Access Token отсутствует или является тестовым. Запускается MOCK-публикация.")
            self._print_mock_github_comment(full_name, pull_number, summary_markdown, inline_comments)
            return True

        url = f"{self.base_url}/repos/{full_name}/pulls/{pull_number}/reviews"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Форматируем комментарии под формат GitHub API
        github_comments = [
            {
                "path": c["file_path"],
                "line": c["line_number"],
                "body": f"**[{c['severity'].upper()}]** {c['comment_text']}"
                + (f"\n```python\n{c['suggested_code']}\n```" if c.get("suggested_code") else ""),
            }
            for c in inline_comments
        ]

        payload = {
            "commit_id": commit_sha,
            "body": summary_markdown,
            "event": event_type,
            "comments": github_comments,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                logger.info(f"✅ AI Review успешно опубликован в PR #{pull_number} ({full_name})!")
                return True
            else:
                logger.error(f"❌ Ошибка публикации в GitHub API [{response.status_code}]: {response.text}")
                return False

    def _print_mock_github_comment(
        self, full_name: str, pull_number: int, summary: str, comments: List[Dict[str, Any]]
    ):
        print("\n" + "🌐 [GITHUB API MOCK RESPONSE]".center(60, "="))
        print(f"📌 Репозиторий: {full_name} | Pull Request #{pull_number}")
        print("-" * 60)
        print(summary)
        print("-" * 60)
        print("💬 Точечные комментарии (Inline Comments):")
        for c in comments:
            print(f"  • {c['file_path']}:{c['line_number']} [{c['severity'].upper()}]")
            print(f"    {c['comment_text']}")
            if c.get("suggested_code"):
                print(f"    💡 Предложение:\n    {c['suggested_code']}")
        print("=" * 60 + "\n")