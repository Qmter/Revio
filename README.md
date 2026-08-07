# 🤖 AI Code Review Assistant

Микросервисная система автоматического ревью кода на основе событийно-ориентированной архитектуры.
Проект принимает вебхуки Pull Request, ставит задачи в очередь, обрабатывает их AI-движком и показывает результат на интерактивном дашборде.

---

## 🏗️ Архитектура

Систему составляют три основных сервиса + инфраструктура контейнеров:

- **backend** — FastAPI сервис для приёма вебхуков, API и публикации событий.
- **ai_engine** — фоновой Python-воркер, который регулярно ищет задачи со статусом `pending`, формирует промпты и отправляет их в LLM.
- **frontend** — React + Vite дашборд, собранный через Nginx.
- **postgres** — хранилище данных.
- **kafka (Redpanda)** — брокер сообщений для обмена событиями между сервисами.

---

## 📁 Структура репозитория

```text
git_review/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── services/
│       ├── ai_engine/
│       └── webhook_ingestion/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── env_example.txt
└── README.md
```

---

## ⚙️ Переменные окружения

Скопируйте `env_example.txt` в `.env` и заполните данные перед запуском:

```powershell
copy env_example.txt .env
```

Обязательные переменные:

- `DB_NAME` — имя базы данных
- `DB_USER` — пользователь PostgreSQL
- `DB_PASSWORD` — пароль
- `DB_HOST` — хост базы данных
- `DB_PORT` — порт базы данных
- `KAFKA_BOOTSTRAP_SERVERS` — адрес Kafka внутри Docker Compose
- `LLM_PROVIDER` — `ollama` или `gemini`
- `OLLAMA_BASE_URL` — URL Ollama
- `OLLAMA_MODEL` — модель Ollama
- `GEMINI_API_KEY` — ключ Google Gemini API

---

## 🤖 Поддерживаемые AI-режимы

### 1. Локальная модель через Ollama

1. Установите и запустите Ollama.
2. Подготовьте модель для анализа кода.
3. В `.env` установите:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://<host_or_container_ip>:11434
OLLAMA_MODEL=<your_model>
```

### 2. Облачный AI через Google Gemini

1. Получите ключ Google Gemini API.
2. В `.env` установите:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your_api_key>
GEMINI_MODEL=gemini-1.5-flash
```

---

## 🚀 Запуск через Docker Compose

Текущий проект запускается через `docker-compose.yml`.

1. Перейдите в корневую директорию проекта:

```powershell
cd C:\Users\username\vsCodeProjects\git_review
```

2. Скопируйте шаблон окружения:

```powershell
copy env_example.txt .env
```

3. Запустите контейнеры:

```powershell
docker compose up --build -d
```

4. Проверьте статус сервисов:

```powershell
docker ps
```

---

## 🌐 Доступные интерфейсы

- Frontend: http://localhost
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

---

## 🧩 Важные сервисы

- `review_backend` — FastAPI сервис, запускается из `backend/Dockerfile`.
- `review_ai_engine` — тот же образ, но с командой `python -m services.ai_engine.main`.
- `review_frontend` — React приложение, собранное и раздаваемое Nginx.
- `review_postgres` — PostgreSQL 16.
- `review_kafka` — Redpanda Kafka.

---

## 🛠️ Разработка

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn services.webhook_ingestion.main:app --host 0.0.0.0 --port 8000
```

---

## 📌 Примечания

- `docker-compose.yml` ожидает, что файл `.env` находится в корне проекта.
- Если используете Ollama, убедитесь, что `OLLAMA_BASE_URL` доступен из контейнеров Docker.
- Kafka доступен внутри Compose по адресу `kafka:29092`.

---

## 📚 Полезные файлы

- `docker-compose.yml` — оркестрация всех сервисов
- `env_example.txt` — шаблон окружения
- `backend/Dockerfile` — образ Python для API и AI Engine
- `frontend/Dockerfile` — сборка React и Nginx
