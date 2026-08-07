# 🤖 AI Code Review Assistant

Микросервисная система автоматического ревью кода с использованием искусственного интеллекта. Проект перехватывает вебхуки от Pull Request'ов, организует асинхронную очередь задач через брокер сообщений, анализирует изменения с помощью языковой модели (локально через **Ollama** или через облачный **Google Gemini API**), отправляет алерты через сервис уведомлений и выводит детальный вердикт с оценками на интерактивный веб-дашборд.

---

## 🏗 Архитектура и стек технологий

Система спроектирована по принципам событийно-ориентированной архитектуры (Event-Driven Architecture) и полностью контейнеризирована:

*   **Backend (API Gateway & Webhook Ingestion)**: FastAPI (Python 3.11), SQLAlchemy (Async), Pydantic, `pyproject.toml`. Принимает вебхуки, управляет сущностями в БД и публикует события в очередь.
*   **AI Engine (Worker Service)**: Асинхронный фоновый воркер, который вычитывает задачи из брокера, формирует промпты, обращается к выбранной LLM (**Ollama** или **Gemini API**) и сохраняет структурированный отчет.
*   **Notifications Service**: Микросервис уведомлений, который слушает события из брокера сообщений (например, завершение ревью) для доставки алертов.
*   **Message Broker**: **Redpanda** (высокопроизводительный брокер сообщений, полностью совместимый с Apache Kafka).
*   **Database**: PostgreSQL 16 для хранения репозиториев, pull request'ов, истории ревью и замечаний.
*   **Frontend**: React (Vite) + Nginx. Современный веб-интерфейс для мониторинга репозиториев и просмотра результатов код-ревью.

---

## 📂 Структура репозитория

```text
git_review/
├── backend/
│   ├── services/
│   │   ├── ai_engine/          # AI-воркер (интеграция с Ollama / Gemini)
│   │   ├── webhook_ingestion/  # FastAPI эндпоинты и обработка вебхуков
│   │   └── notifications/      # Сервис уведомлений и алертов
│   ├── shared/                 # Общие модели БД, конфигурации, схемы
│   ├── Dockerfile              # Сборка через pyproject.toml
│   └── pyproject.toml          # Современный менеджер зависимостей (PEP 621)
├── frontend/                   # React (Vite) + Nginx дашборд
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml          # Оркестрация всех сервисов
└── env_example.txt             # Шаблон переменных окружения

```

---

## ⚙️ Конфигурация AI (Ollama vs. Gemini API)

Проект поддерживает два режима работы искусственного интеллекта. Вы можете выбрать один из них в файле `.env`:

### Вариант 1: Локальная модель через Ollama (Офлайн / Бесплатно)

1. Установите и запустите [Ollama](https://ollama.com/).
2. Скачайте модель для работы с кодом:
```powershell
ollama run qwen2.5-coder:7b

```


3. В файле `.env` укажите параметры:
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://<ваш_ip_компьютера>:11434
OLLAMA_MODEL=qwen2.5-coder:7b

```



### Вариант 2: Облачный AI через Google Gemini API (Быстро / Без нагрузки на ПК)

1. Получите ключ в [Google AI Studio](https://aistudio.google.com/).
2. В файле `.env` укажите ключ:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyYourActualApiKeyHere
GEMINI_MODEL=gemini-1.5-flash

```



---

## 🚀 Инструкция по развертыванию (Docker Compose)

### Требования

* Установленный **Docker** и **Docker Desktop** (с поддержкой WSL2 для Windows).

### Шаги запуска

1. **Клонируйте репозиторий и перейдите в папку проекта:**
```powershell
cd c:\Users\yaroslav\vsCodeProjects\git_review

```


2. **Создайте файл конфигурации `.env`:**
Скопируйте `env_example.txt` в `.env` и заполните своими данными:
```powershell
copy env_example.txt .env

```


3. **Соберите и запустите все контейнеры:**
```powershell
docker compose up --build -d

```


4. **Проверьте статусы контейнеров:**
```powershell
docker ps

```


Все сервисы должны перейти в состояние `Running` / `Healthy`.

---

## 🌐 Использование

* **Веб-дашборд (Frontend):** [http://localhost](http://localhost)
* **Документация API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)

```
