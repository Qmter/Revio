import json
import logging
from typing import Any, Dict
import httpx

from shared.config import settings
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.gemini_key = settings.GEMINI_API_KEY
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL

    async def analyze_code(self, git_diff: str, custom_rules: dict) -> Dict[str, Any]:
        """
        Главная точка входа. Вызывает выбранный LLM провайдер.
        """
        user_prompt = build_user_prompt(git_diff, custom_rules)

        if self.provider == "gemini" and self.gemini_key:
            try:
                return await self._call_gemini(user_prompt)
            except Exception as e:
                logger.error(f"❌ Ошибка вызова Gemini API: {e}. Переключаемся на Mock.")
                return self._generate_mock_review(git_diff)

        elif self.provider == "ollama":
            try:
                return await self._call_ollama(user_prompt)
            except Exception as e:
                logger.error(f"❌ Ошибка вызова Ollama ({self.ollama_url}): {e}. Переключаемся на Mock.")
                return self._generate_mock_review(git_diff)

        else:
            logger.warning(f"⚠️ Провайдер '{self.provider}' не настроен или ключ отсутствует. Используем Mock.")
            return self._generate_mock_review(git_diff)

    async def _call_gemini(self, user_prompt: str) -> Dict[str, Any]:
        """Вызов Google Gemini API с требованием вернуть строго JSON."""
        # Используем современную модель gemini-1.5-pro (или gemini-1.5-flash)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={self.gemini_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",  # Требуем JSON от Gemini
                "temperature": 0.2
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Извлекаем текст ответа Gemini
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Считаем токеноемкость (если Gemini отдалаUsageMetadata)
            tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)
            
            parsed_json = json.loads(raw_text)
            parsed_json["tokens_used"] = tokens_used
            return parsed_json

    async def _call_ollama(self, user_prompt: str) -> Dict[str, Any]:
        """Вызов локальной Ollama API."""
        url = f"{self.ollama_url}/api/chat"
        
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",  # Принудительный JSON режим в Ollama
            "stream": False
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            raw_text = data["message"]["content"]
            parsed_json = json.loads(raw_text)
            parsed_json["tokens_used"] = data.get("eval_count", 0)
            return parsed_json

    def _generate_mock_review(self, git_diff: str) -> Dict[str, Any]:
        """Заглушка для локального тестирования без обращения к сетям."""
        return {
            "summary": "Код написан аккуратно, но найдены потенциальные проблемы с закрытием ресурсов и обработкой асинхронных ошибок.",
            "score": 82,
            "comments": [
                {
                    "file_path": "services/webhook_ingestion/kafka.py",
                    "line_number": 18,
                    "severity": "warning",
                    "comment_text": "AIOKafkaProducer не закрывается при вызове исключения. Рекомендуется вызвать await producer.stop() в блоке except.",
                    "suggested_code": "except Exception:\n    await producer.stop()\n    self.producer = None",
                },
                {
                    "file_path": "services/webhook_ingestion/router.py",
                    "line_number": 52,
                    "severity": "info",
                    "comment_text": "Желательно добавить логирование IP-адресов входящих вебхуков.",
                    "suggested_code": "logger.info(f'Webhook received from {request.client.host}')",
                }
            ],
            "tokens_used": 0,
        }


llm_client = LLMClient()